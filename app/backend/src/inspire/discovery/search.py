"""Busca com filtros e facetas sobre `analitico.conjunto_busca` (ADR-0008).

Os nomes de colunas vêm de listas fixas (nunca do usuário); valores sempre por parâmetro.
"""

from __future__ import annotations

from dataclasses import dataclass, fields
from typing import Any

from sqlalchemy import Engine, text

SORTS = {
    "relevancia": "rank DESC, b.titulo",
    "titulo": "b.titulo",
    "nota": "b.nota_qualidade DESC NULLS LAST, b.titulo",
    "nota_asc": "b.nota_qualidade ASC NULLS LAST, b.titulo",
    "prioridade": "b.prioridade DESC NULLS LAST, b.titulo",
    "atualizacao": "b.metadados_atualizados_em DESC NULLS LAST, b.titulo",
}
MAX_PAGE_SIZE = 100
FACET_LIMIT = 30


@dataclass
class Filters:
    q: str | None = None
    organizacao: str | None = None
    esfera: str | None = None
    uf: str | None = None
    tema: str | None = None
    tag: str | None = None
    formato: str | None = None
    licenca: str | None = None
    periodicidade: str | None = None
    selo: str | None = None
    estado_curadoria: str | None = None
    nota_min: float | None = None
    nota_max: float | None = None
    curado: bool | None = None
    sem_detalhe: bool | None = None
    atualizado_portal: str | None = None
    incluir_removidos: bool = False
    colecao: int | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Filters:
        allowed = {f.name for f in fields(cls)}
        return cls(**{k: v for k, v in data.items() if k in allowed and v not in (None, "")})

    def to_dict(self) -> dict[str, Any]:
        return {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if getattr(self, f.name) not in (None, False)
        }


# filtro -> (expressão SQL com :parâmetro)
_SCALAR = {
    "organizacao": "b.organizacao_slug = :organizacao",
    "esfera": "b.esfera = :esfera",
    "uf": "b.uf = :uf",
    "licenca": "b.licenca = :licenca",
    "periodicidade": "b.periodicidade = :periodicidade",
    "selo": "b.selo_portal = :selo",
    "estado_curadoria": "b.estado_curadoria = :estado_curadoria",
    "atualizado_portal": "b.atualizado_portal = :atualizado_portal",
    "tema": "b.temas && string_to_array(:tema, ',')",  # vários temas separados por vírgula: qualquer um deles
    "tag": ":tag = ANY(b.tags)",
    "formato": "upper(:formato) = ANY(b.formatos)",
}
# faceta -> (filtro correspondente, expressão da coluna, é array, rótulo)
_FACETS = {
    "organizacao": ("organizacao", "b.organizacao_slug", False, "min(b.organizacao_titulo)"),
    "esfera": ("esfera", "b.esfera", False, None),
    "uf": ("uf", "b.uf", False, None),
    "tema": ("tema", "b.temas", True, None),
    "formato": ("formato", "b.formatos", True, None),
    "licenca": ("licenca", "b.licenca", False, None),
    "periodicidade": ("periodicidade", "b.periodicidade", False, None),
    "selo": ("selo", "b.selo_portal", False, None),
    "estado_curadoria": ("estado_curadoria", "b.estado_curadoria", False, None),
}


class SearchService:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    # ------------------------------------------------------------------ construção do WHERE

    def _where(self, f: Filters, params: dict[str, Any], *, skip: str | None = None) -> list[str]:
        clauses: list[str] = []
        if not f.incluir_removidos:
            clauses.append("NOT b.removido")
        for name, sql in _SCALAR.items():
            value = getattr(f, name)
            if value is not None and name != skip:
                clauses.append(sql)
                params[name] = value
        if f.nota_min is not None:
            clauses.append("b.nota_qualidade >= :nota_min")
            params["nota_min"] = f.nota_min
        if f.nota_max is not None:
            clauses.append("b.nota_qualidade <= :nota_max")
            params["nota_max"] = f.nota_max
        if f.curado is not None:
            clauses.append("b.curado = :curado")
            params["curado"] = f.curado
        if f.sem_detalhe is not None:
            clauses.append("b.sem_detalhe = :sem_detalhe")
            params["sem_detalhe"] = f.sem_detalhe
        if f.colecao is not None:
            clauses.append(self._collection_clause(f.colecao, params))
        return clauses

    def _collection_clause(self, collection_id: int, params: dict[str, Any]) -> str:
        with self._engine.connect() as conn:
            col = conn.execute(
                text("SELECT tipo, regra_filtro FROM curadoria.colecao WHERE id = :c"),
                {"c": collection_id},
            ).first()
        params["col_id"] = collection_id
        if col is None:
            return "false"
        included = "b.id IN (SELECT conjunto_id FROM curadoria.colecao_item WHERE colecao_id = :col_id AND modo = 'incluir')"
        if col.tipo == "manual":
            return included
        rule = Filters.from_dict(dict(col.regra_filtro))
        rule.colecao = None
        rule_params: dict[str, Any] = {}
        rule_clauses = self._where(rule, rule_params)
        # parâmetros da regra recebem prefixo para não colidir com os do filtro principal
        sql = " AND ".join(rule_clauses) or "true"
        for key in sorted(rule_params, key=len, reverse=True):
            sql = sql.replace(f":{key}", f":r_{key}")
            params[f"r_{key}"] = rule_params[key]
        excluded = "b.id NOT IN (SELECT conjunto_id FROM curadoria.colecao_item WHERE colecao_id = :col_id AND modo = 'excluir')"
        return f"(({sql}) AND {excluded} OR {included})"

    # ------------------------------------------------------------------ busca

    def search(
        self, f: Filters, *, page: int = 1, size: int = 20, sort: str = "relevancia"
    ) -> dict[str, Any]:
        page, size = max(1, page), max(1, min(size, MAX_PAGE_SIZE))
        params: dict[str, Any] = {}
        clauses = self._where(f, params)
        query = (f.q or "").strip()
        approximate = False
        rank_sql = "0::real"
        if query:
            params["q"] = query
            fts = "b.tsv @@ websearch_to_tsquery('portuguese', public.f_busca(:q))"
            if self._count([*clauses, fts], params) == 0:
                approximate = True
                fts = "public.f_unaccent(lower(b.titulo)) % public.f_unaccent(lower(:q))"
                rank_sql = (
                    "similarity(public.f_unaccent(lower(b.titulo)), public.f_unaccent(lower(:q)))"
                )
            else:
                rank_sql = (
                    "ts_rank_cd(b.tsv, websearch_to_tsquery('portuguese', public.f_busca(:q)))"
                )
            clauses.append(fts)
        where = " AND ".join(clauses) or "true"
        order = (
            SORTS.get(sort, SORTS["relevancia"])
            if query
            else SORTS.get(sort if sort != "relevancia" else "titulo")
        )
        with self._engine.connect() as conn:
            total = conn.execute(
                text(f"SELECT count(*) FROM analitico.conjunto_busca b WHERE {where}"), params
            ).scalar_one()
            rows = conn.execute(
                text(
                    f"SELECT b.id, b.titulo, left(b.descricao, 300) AS resumo, b.organizacao_slug, b.organizacao_titulo, "
                    f"b.esfera, b.uf, b.temas, b.formatos, b.tags, b.licenca, b.periodicidade, b.nota_qualidade, b.prioridade, "
                    f"b.estado_curadoria, b.curado, b.selo_portal, b.sem_detalhe, b.removido, b.qtd_recursos, "
                    f"b.metadados_atualizados_em, {rank_sql} AS rank FROM analitico.conjunto_busca b "
                    f"WHERE {where} ORDER BY {order} LIMIT :limit OFFSET :offset"
                ),
                {**params, "limit": size, "offset": (page - 1) * size},
            ).all()
        return {
            "total": total,
            "pagina": page,
            "tamanho": size,
            "aproximada": approximate,
            "itens": [{k: v for k, v in r._mapping.items() if k != "rank"} for r in rows],
            "facetas": self._facets(f, query, approximate),
        }

    def ids(self, f: Filters, limit: int = 100000) -> list[str]:
        """Todos os ids que a busca devolveria (para coleções e operações em lote)."""
        params: dict[str, Any] = {}
        clauses = self._where(f, params)
        query = (f.q or "").strip()
        if query:
            params["q"] = query
            clauses.append("b.tsv @@ websearch_to_tsquery('portuguese', public.f_busca(:q))")
        where = " AND ".join(clauses) or "true"
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    f"SELECT b.id FROM analitico.conjunto_busca b WHERE {where} ORDER BY b.id LIMIT :n"
                ),
                {**params, "n": limit},
            )
            return [r.id for r in rows]

    def _count(self, clauses: list[str], params: dict[str, Any]) -> int:
        where = " AND ".join(clauses) or "true"
        with self._engine.connect() as conn:
            return int(
                conn.execute(
                    text(f"SELECT count(*) FROM analitico.conjunto_busca b WHERE {where}"), params
                ).scalar_one()
            )

    # ------------------------------------------------------------------ facetas

    def _facets(self, f: Filters, query: str, approximate: bool) -> dict[str, list[dict[str, Any]]]:
        result: dict[str, list[dict[str, Any]]] = {}
        with self._engine.connect() as conn:
            for name, (flt, col, is_array, label) in _FACETS.items():
                params: dict[str, Any] = {}
                clauses = self._where(f, params, skip=flt)
                if query:
                    params["q"] = query
                    clauses.append(
                        "public.f_unaccent(lower(b.titulo)) % public.f_unaccent(lower(:q))"
                        if approximate
                        else "b.tsv @@ websearch_to_tsquery('portuguese', public.f_busca(:q))"
                    )
                where = " AND ".join(clauses) or "true"
                label_sql = label or "NULL"
                if is_array:
                    sql = (
                        f"SELECT v AS valor, NULL AS rotulo, count(*) AS n FROM analitico.conjunto_busca b, "
                        f"unnest({col}) v WHERE {where} GROUP BY v ORDER BY n DESC, v LIMIT {FACET_LIMIT}"
                    )
                else:
                    sql = (
                        f"SELECT {col} AS valor, {label_sql} AS rotulo, count(*) AS n FROM analitico.conjunto_busca b "
                        f"WHERE {where} AND {col} IS NOT NULL GROUP BY {col} ORDER BY n DESC, {col} LIMIT {FACET_LIMIT}"
                    )
                result[name] = [
                    {"valor": r.valor, "rotulo": r.rotulo or r.valor, "n": r.n}
                    for r in conn.execute(text(sql), params)
                ]
        return result
