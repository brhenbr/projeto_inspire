"""Alterações curadas e status de revisão. O espelho do portal nunca é alterado (ADR-0010)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Connection, Engine, text

from inspire.quality import service as quality

EDITABLE = ("titulo", "descricao", "tags", "temas", "periodicidade", "licenca")
STATES = ("pendente", "em_revisao", "aprovado", "rejeitado", "duplicado")
LIMITS = {"titulo": 500, "descricao": 20000, "periodicidade": 60, "licenca": 60}
MAX_TAGS = 50
MAX_TAG_LEN = 100


class CurationError(ValueError):
    """Pedido de curadoria inválido (vira HTTP 422 na API)."""


class NotFoundError(LookupError):
    pass


def _validate(conn: Connection, campo: str, valor: Any) -> Any:
    if campo not in EDITABLE:
        raise CurationError(f"Campo não editável: {campo}")
    if campo in ("tags", "temas"):
        if not isinstance(valor, list) or not all(isinstance(x, str) for x in valor):
            raise CurationError(f"'{campo}' deve ser uma lista de textos")
        items = sorted({x.strip() for x in valor if x.strip()})
        if campo == "tags":
            if len(items) > MAX_TAGS or any(len(x) > MAX_TAG_LEN for x in items):
                raise CurationError(f"No máximo {MAX_TAGS} tags de até {MAX_TAG_LEN} caracteres")
        else:
            known = {r.slug for r in conn.execute(text("SELECT slug FROM catalogo.tema"))}
            unknown = [x for x in items if x not in known]
            if unknown:
                raise CurationError(f"Tema(s) desconhecido(s): {', '.join(unknown)}")
        return items
    if valor is None:
        return None
    if not isinstance(valor, str):
        raise CurationError(f"'{campo}' deve ser um texto")
    cleaned = valor.strip()
    if campo in ("titulo",) and not cleaned:
        raise CurationError("O título não pode ficar vazio")
    if len(cleaned) > LIMITS[campo]:
        raise CurationError(f"'{campo}' passa de {LIMITS[campo]} caracteres")
    return cleaned or None


def _current(conn: Connection, dataset_id: str) -> tuple[Any, dict[str, Any]]:
    """Linha efetiva (modelo de leitura) e valores originais do espelho."""
    eff = conn.execute(
        text(
            "SELECT titulo, descricao, licenca, periodicidade, tags, temas, estado_curadoria "
            "FROM analitico.conjunto_busca WHERE id = :id"
        ),
        {"id": dataset_id},
    ).first()
    orig = conn.execute(
        text(
            "SELECT titulo, descricao, licenca, periodicidade FROM catalogo.conjunto WHERE id = :id"
        ),
        {"id": dataset_id},
    ).first()
    if eff is None or orig is None:
        raise NotFoundError(dataset_id)
    original = dict(orig._mapping)
    original["tags"] = sorted(
        r.tag_nome
        for r in conn.execute(
            text("SELECT tag_nome FROM catalogo.conjunto_tag WHERE conjunto_id = :id"),
            {"id": dataset_id},
        )
    )
    original["temas"] = sorted(
        r.tema_slug
        for r in conn.execute(
            text("SELECT tema_slug FROM catalogo.conjunto_tema WHERE conjunto_id = :id"),
            {"id": dataset_id},
        )
    )
    return eff, original


def apply_changes(
    engine: Engine,
    dataset_id: str,
    changes: dict[str, Any],
    *,
    author: str,
    origin: str = "humano",
    comment: str | None = None,
    proposal_id: int | None = None,
) -> list[str]:
    """Aplica alterações de campos. Devolve os campos que realmente mudaram (iguais ao efetivo são ignorados)."""
    if not changes:
        raise CurationError("Nenhuma alteração informada")
    changed: list[str] = []
    with engine.begin() as conn:
        eff, original = _current(conn, dataset_id)
        for campo, raw in changes.items():
            value = _validate(conn, campo, raw)
            effective = eff._mapping[campo]
            effective = sorted(effective) if campo in ("tags", "temas") else effective
            if value == effective:
                continue
            # valor igual ao original vira reversão (não marca "curado" sem diferença real)
            stored = None if value == original[campo] else value
            conn.execute(
                text(
                    "INSERT INTO curadoria.alteracao (conjunto_id, campo, valor, origem, proposta_id, autor, comentario) "
                    "VALUES (:c, :campo, CAST(:v AS jsonb), :o, :p, :a, :cm)"
                ),
                {
                    "c": dataset_id,
                    "campo": campo,
                    "v": None if stored is None else json.dumps(stored, ensure_ascii=False),
                    "o": origin,
                    "p": proposal_id,
                    "a": author,
                    "cm": comment,
                },
            )
            changed.append(campo)
        if changed and eff.estado_curadoria == "pendente":
            _upsert_status(conn, dataset_id, "em_revisao", None, author)
    if changed:
        quality.recompute(engine, [dataset_id])
    return changed


def revert_field(engine: Engine, dataset_id: str, campo: str, *, author: str) -> bool:
    """Volta um campo ao valor do portal. Devolve False se ele já estava igual ao original."""
    if campo not in EDITABLE:
        raise CurationError(f"Campo não editável: {campo}")
    with engine.begin() as conn:
        _current(conn, dataset_id)
        has = conn.execute(
            text(
                "SELECT valor IS NOT NULL AS ativo FROM curadoria.alteracao WHERE conjunto_id = :c AND campo = :f "
                "ORDER BY id DESC LIMIT 1"
            ),
            {"c": dataset_id, "f": campo},
        ).first()
        if has is None or not has.ativo:
            return False
        conn.execute(
            text(
                "INSERT INTO curadoria.alteracao (conjunto_id, campo, valor, origem, autor, comentario) "
                "VALUES (:c, :f, NULL, 'humano', :a, 'Reversão ao valor do portal')"
            ),
            {"c": dataset_id, "f": campo, "a": author},
        )
    quality.recompute(engine, [dataset_id])
    return True


def _upsert_status(
    conn: Connection, dataset_id: str, state: str, duplicate_of: str | None, author: str
) -> None:
    conn.execute(
        text(
            "INSERT INTO curadoria.status_conjunto (conjunto_id, estado, duplicado_de, atualizado_por) "
            "VALUES (:c, :s, :d, :a) ON CONFLICT (conjunto_id) DO UPDATE SET estado = EXCLUDED.estado, "
            "duplicado_de = EXCLUDED.duplicado_de, atualizado_em = now(), atualizado_por = EXCLUDED.atualizado_por"
        ),
        {"c": dataset_id, "s": state, "d": duplicate_of, "a": author},
    )


def set_status(
    engine: Engine, dataset_id: str, state: str, *, author: str, duplicate_of: str | None = None
) -> None:
    if state not in STATES:
        raise CurationError(f"Estado inválido: {state}")
    if state == "duplicado" and duplicate_of is not None and duplicate_of == dataset_id:
        raise CurationError("Um conjunto não pode ser duplicado de si mesmo")
    with engine.begin() as conn:
        _current(conn, dataset_id)
        if (
            duplicate_of is not None
            and not conn.execute(
                text("SELECT 1 FROM catalogo.conjunto WHERE id = :d"), {"d": duplicate_of}
            ).first()
        ):
            raise CurationError("O conjunto original da duplicidade não existe")
        _upsert_status(
            conn, dataset_id, state, duplicate_of if state == "duplicado" else None, author
        )
    quality.refresh_for(engine, [dataset_id])


def set_status_bulk(engine: Engine, ids: list[str], state: str, *, author: str) -> int:
    if state not in STATES or state == "duplicado":
        raise CurationError("Estado inválido para operação em lote")
    with engine.begin() as conn:
        found = [
            r.id
            for r in conn.execute(
                text("SELECT id FROM catalogo.conjunto WHERE id = ANY(:ids)"), {"ids": ids}
            )
        ]
        for i in found:
            _upsert_status(conn, i, state, None, author)
    quality.refresh_for(engine, found)
    return len(found)


def on_source_changed(engine: Engine, dataset_id: str) -> None:
    """O portal mudou o conjunto: aprovado volta a pendente e propostas de LLM pendentes ficam desatualizadas."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE curadoria.status_conjunto SET estado = 'pendente', atualizado_em = now(), "
                "atualizado_por = 'sistema' WHERE conjunto_id = :c AND estado = 'aprovado'"
            ),
            {"c": dataset_id},
        )
        conn.execute(
            text(
                "UPDATE curadoria.llm_proposta SET estado = 'desatualizada' "
                "WHERE conjunto_id = :c AND estado = 'pendente'"
            ),
            {"c": dataset_id},
        )
