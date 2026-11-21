"""Detalhe do conjunto, organizações e painel (leituras)."""

from __future__ import annotations

from typing import Any

from sqlalchemy import Engine, text

PORTAL_DATASET_URL = "https://dados.gov.br/dados/conjuntos-dados/"


def get_dataset(engine: Engine, dataset_id: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        c = conn.execute(
            text(
                "SELECT c.*, o.titulo AS organizacao_titulo, o.esfera, o.uf, o.municipio "
                "FROM catalogo.conjunto c LEFT JOIN catalogo.organizacao o ON o.slug = c.organizacao_slug "
                "WHERE c.id = :id"
            ),
            {"id": dataset_id},
        ).first()
        if c is None:
            return None
        b = conn.execute(
            text("SELECT * FROM analitico.conjunto_busca WHERE id = :id"), {"id": dataset_id}
        ).first()
        recursos = conn.execute(
            text(
                "SELECT id, titulo, descricao, formato, tipo, link, nome_arquivo, tamanho, downloads, ordem, "
                "catalogado_em, atualizado_em FROM catalogo.recurso WHERE conjunto_id = :id ORDER BY ordem NULLS LAST, titulo"
            ),
            {"id": dataset_id},
        ).all()
        orig_tags = [
            r.tag_nome
            for r in conn.execute(
                text(
                    "SELECT tag_nome FROM catalogo.conjunto_tag WHERE conjunto_id = :id ORDER BY 1"
                ),
                {"id": dataset_id},
            )
        ]
        orig_temas = [
            r.tema_slug
            for r in conn.execute(
                text(
                    "SELECT tema_slug FROM catalogo.conjunto_tema WHERE conjunto_id = :id ORDER BY 1"
                ),
                {"id": dataset_id},
            )
        ]
        assoc = [
            r.associado_id
            for r in conn.execute(
                text(
                    "SELECT associado_id FROM catalogo.conjunto_associado WHERE conjunto_id = :id"
                ),
                {"id": dataset_id},
            )
        ]
        history = conn.execute(
            text(
                "SELECT evento, em, execucao_id FROM catalogo.conjunto_historico WHERE conjunto_id = :id ORDER BY id DESC LIMIT 50"
            ),
            {"id": dataset_id},
        ).all()
        alteracoes = conn.execute(
            text(
                "SELECT id, campo, valor, origem, autor, comentario, em, proposta_id FROM curadoria.alteracao "
                "WHERE conjunto_id = :id ORDER BY id DESC LIMIT 100"
            ),
            {"id": dataset_id},
        ).all()
        status = conn.execute(
            text(
                "SELECT estado, duplicado_de, atualizado_em, atualizado_por FROM curadoria.status_conjunto WHERE conjunto_id = :id"
            ),
            {"id": dataset_id},
        ).first()
        quality = conn.execute(
            text(
                "SELECT nota, dimensoes, detalhes, calculada_em FROM analitico.qualidade_conjunto WHERE conjunto_id = :id"
            ),
            {"id": dataset_id},
        ).first()
        pending = conn.execute(
            text(
                "SELECT count(*) FROM curadoria.llm_proposta WHERE conjunto_id = :id AND estado = 'pendente'"
            ),
            {"id": dataset_id},
        ).scalar_one()
        collections = conn.execute(
            text(
                "SELECT col.id, col.nome FROM curadoria.colecao col JOIN curadoria.colecao_item i ON i.colecao_id = col.id "
                "WHERE i.conjunto_id = :id AND i.modo = 'incluir'"
            ),
            {"id": dataset_id},
        ).all()
    return {
        "id": c.id,
        "slug": c.slug,
        "link_portal": f"{PORTAL_DATASET_URL}{c.slug}" if c.slug else None,
        "sem_detalhe": c.sem_detalhe,
        "removido_em": c.removido_em,
        "efetivo": None
        if b is None
        else {
            "titulo": b.titulo,
            "descricao": b.descricao,
            "licenca": b.licenca,
            "periodicidade": b.periodicidade,
            "tags": list(b.tags),
            "temas": list(b.temas),
        },
        "original": {
            "titulo": c.titulo,
            "descricao": c.descricao,
            "licenca": c.licenca,
            "periodicidade": c.periodicidade,
            "tags": orig_tags,
            "temas": orig_temas,
        },
        "organizacao": {
            "slug": c.organizacao_slug,
            "titulo": c.organizacao_titulo,
            "esfera": c.esfera,
            "uf": c.uf,
            "municipio": c.municipio,
        },
        "portal": {
            "selo": c.selo_portal,
            "atualizado": c.atualizado_portal,
            "dados_abertos": c.dados_abertos,
            "origem_cadastro": c.origem_cadastro,
            "visibilidade": c.visibilidade,
            "versao": c.versao,
            "descontinuado": c.descontinuado,
            "observancia_legal": c.observancia_legal,
            "cobertura_temporal_inicio": c.cobertura_temporal_inicio,
            "cobertura_temporal_fim": c.cobertura_temporal_fim,
            "cobertura_espacial": c.cobertura_espacial,
            "granularidade_espacial": c.granularidade_espacial,
            "catalogado_em": c.catalogado_em,
            "metadados_atualizados_em": c.metadados_atualizados_em,
            "dados_atualizados_em": c.dados_atualizados_em,
            "tem_responsavel": c.tem_responsavel,
            "tem_email_responsavel": c.tem_email_responsavel,
        },
        "recursos": [dict(r._mapping) for r in recursos],
        "associados": assoc,
        "estado_curadoria": (status.estado if status else "pendente"),
        "status": None if status is None else dict(status._mapping),
        "alteracoes": [dict(a._mapping) for a in alteracoes],
        "propostas_pendentes": pending,
        "colecoes": [dict(x._mapping) for x in collections],
        "qualidade": None
        if quality is None
        else {
            "nota": float(quality.nota),
            "dimensoes": quality.dimensoes,
            "detalhes": quality.detalhes,
            "calculada_em": quality.calculada_em,
        },
        "historico": [dict(h._mapping) for h in history],
    }


def list_organizations(
    engine: Engine,
    *,
    q: str | None = None,
    esfera: str | None = None,
    page: int = 1,
    size: int = 20,
    sort: str = "conjuntos",
) -> dict[str, Any]:
    order = {
        "conjuntos": "conjuntos DESC, titulo",
        "nome": "titulo",
        "nota": "nota_media ASC NULLS LAST, titulo",
        "curados": "curados DESC, titulo",
    }.get(sort, "conjuntos DESC, titulo")
    where = ["NOT b.removido", "b.organizacao_slug IS NOT NULL"]
    params: dict[str, Any] = {}
    if q:
        where.append(
            "public.f_unaccent(lower(b.organizacao_titulo)) LIKE '%' || public.f_unaccent(lower(:q)) || '%'"
        )
        params["q"] = q
    if esfera:
        where.append("b.esfera = :esfera")
        params["esfera"] = esfera
    size = max(1, min(size, 100))
    base = (
        "SELECT b.organizacao_slug AS slug, min(b.organizacao_titulo) AS titulo, min(b.esfera) AS esfera, "
        "min(b.uf) AS uf, count(*) AS conjuntos, round(avg(b.nota_qualidade), 1) AS nota_media, "
        "count(*) FILTER (WHERE b.curado) AS curados, "
        "count(*) FILTER (WHERE b.estado_curadoria = 'aprovado') AS aprovados, "
        "count(*) FILTER (WHERE b.sem_detalhe) AS sem_detalhe "
        f"FROM analitico.conjunto_busca b WHERE {' AND '.join(where)} GROUP BY b.organizacao_slug"
    )
    with engine.connect() as conn:
        total = conn.execute(text(f"SELECT count(*) FROM ({base}) t"), params).scalar_one()
        rows = conn.execute(
            text(f"SELECT * FROM ({base}) t ORDER BY {order} LIMIT :n OFFSET :o"),
            {**params, "n": size, "o": (max(1, page) - 1) * size},
        ).all()
    return {
        "total": total,
        "pagina": max(1, page),
        "tamanho": size,
        "itens": [dict(r._mapping) for r in rows],
    }


def get_organization(engine: Engine, slug: str) -> dict[str, Any] | None:
    with engine.connect() as conn:
        org = conn.execute(
            text(
                "SELECT slug, titulo, descricao, esfera, uf, municipio, qtd_declarada FROM catalogo.organizacao WHERE slug = :s"
            ),
            {"s": slug},
        ).first()
        if org is None:
            return None
        resumo = conn.execute(
            text(
                "SELECT count(*) AS conjuntos, round(avg(nota_qualidade), 1) AS nota_media, "
                "count(*) FILTER (WHERE curado) AS curados, "
                "count(*) FILTER (WHERE estado_curadoria = 'aprovado') AS aprovados, "
                "count(*) FILTER (WHERE sem_detalhe) AS sem_detalhe "
                "FROM analitico.conjunto_busca WHERE organizacao_slug = :s AND NOT removido"
            ),
            {"s": slug},
        ).one()
        falhas = conn.execute(
            text(
                "SELECT d->>'regra' AS regra, d->>'nome' AS nome, d->>'dimensao' AS dimensao, count(*) AS conjuntos "
                "FROM analitico.qualidade_conjunto q JOIN analitico.conjunto_busca b ON b.id = q.conjunto_id, "
                "jsonb_array_elements(q.detalhes) d "
                "WHERE b.organizacao_slug = :s AND NOT b.removido AND d->>'passou' = 'false' "
                "GROUP BY 1, 2, 3 ORDER BY conjuntos DESC LIMIT 8"
            ),
            {"s": slug},
        ).all()
        dims = conn.execute(
            text(
                "SELECT k AS dimensao, round(avg(v::numeric), 1) AS nota FROM analitico.qualidade_conjunto q "
                "JOIN analitico.conjunto_busca b ON b.id = q.conjunto_id, jsonb_each_text(q.dimensoes) AS e(k, v) "
                "WHERE b.organizacao_slug = :s AND NOT b.removido GROUP BY k ORDER BY k"
            ),
            {"s": slug},
        ).all()
    return {
        **dict(org._mapping),
        "resumo": dict(resumo._mapping),
        "regras_que_mais_falham": [dict(f._mapping) for f in falhas],
        "dimensoes": [dict(d._mapping) for d in dims],
    }


def dashboard(engine: Engine) -> dict[str, Any]:
    with engine.connect() as conn:
        totals = conn.execute(
            text(
                "SELECT count(*) FILTER (WHERE NOT removido) AS conjuntos, "
                "count(*) FILTER (WHERE removido) AS removidos, "
                "count(*) FILTER (WHERE sem_detalhe AND NOT removido) AS sem_detalhe, "
                "count(*) FILTER (WHERE curado AND NOT removido) AS curados, "
                "count(DISTINCT organizacao_slug) FILTER (WHERE NOT removido) AS organizacoes, "
                "round(avg(nota_qualidade) FILTER (WHERE NOT removido), 1) AS nota_media, "
                "COALESCE(sum(qtd_recursos) FILTER (WHERE NOT removido), 0) AS recursos "
                "FROM analitico.conjunto_busca"
            )
        ).one()

        def group(col: str, array: bool = False, limit: int = 12) -> list[dict[str, Any]]:
            if array:
                sql = f"SELECT v AS valor, count(*) AS n FROM analitico.conjunto_busca, unnest({col}) v WHERE NOT removido GROUP BY v ORDER BY n DESC LIMIT {limit}"
            else:
                sql = f"SELECT {col} AS valor, count(*) AS n FROM analitico.conjunto_busca WHERE NOT removido AND {col} IS NOT NULL GROUP BY 1 ORDER BY n DESC LIMIT {limit}"
            return [dict(r._mapping) for r in conn.execute(text(sql))]

        buckets = conn.execute(
            text(
                "SELECT least(floor(nota_qualidade / 20), 4)::int AS faixa, count(*) AS n FROM analitico.conjunto_busca "
                "WHERE NOT removido AND nota_qualidade IS NOT NULL GROUP BY 1 ORDER BY 1"
            )
        ).all()
        status = conn.execute(
            text(
                "SELECT estado_curadoria AS valor, count(*) AS n FROM analitico.conjunto_busca WHERE NOT removido GROUP BY 1"
            )
        ).all()
        last = conn.execute(
            text(
                "SELECT id, tipo, estado, iniciada_em, finalizada_em, totais->>'listados' AS listados, "
                "totais->>'novos' AS novos, totais->>'alterados' AS alterados, totais->>'removidos' AS removidos "
                "FROM raw.execucao WHERE estado IN ('concluida', 'concluida_com_divergencias') ORDER BY id DESC LIMIT 1"
            )
        ).first()
        faixas = {int(r.faixa): r.n for r in buckets}
        return {
            "totais": dict(totals._mapping),
            "por_esfera": group("esfera"),
            "por_tema": group("temas", array=True),
            "por_formato": group("formatos", array=True),
            "por_licenca": group("licenca"),
            "por_periodicidade": group("periodicidade"),
            "qualidade_faixas": [
                {"faixa": f"{i * 20}-{i * 20 + 20 if i < 4 else 100}", "n": faixas.get(i, 0)}
                for i in range(5)
            ],
            "por_estado_curadoria": [dict(r._mapping) for r in status],
            "ultima_extracao": None if last is None else dict(last._mapping),
        }
