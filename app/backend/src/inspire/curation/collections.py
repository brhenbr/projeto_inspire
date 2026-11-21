"""Coleções manuais e dinâmicas (filtros salvos), com diferença desde a última extração (US-033, US-036)."""

from __future__ import annotations

import json
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from inspire.curation.service import CurationError, NotFoundError
from inspire.discovery.search import Filters, SearchService


def _row(r: Any, members: int | None = None) -> dict[str, Any]:
    out = {
        "id": r.id,
        "nome": r.nome,
        "descricao": r.descricao,
        "responsavel": r.responsavel,
        "tipo": r.tipo,
        "regra_filtro": r.regra_filtro,
        "criada_em": r.criada_em,
        "diff": r.ultimo_diff,
    }
    if members is not None:
        out["conjuntos"] = members
    return out


def _count(engine: Engine, collection_id: int) -> int:
    return int(SearchService(engine).search(Filters(colecao=collection_id), size=1)["total"])


def create(
    engine: Engine,
    name: str,
    *,
    kind: str,
    description: str | None = None,
    owner: str | None = None,
    rule: dict[str, Any] | None = None,
) -> int:
    name = name.strip()
    if not name:
        raise CurationError("O nome da coleção é obrigatório")
    if kind not in ("manual", "dinamica"):
        raise CurationError("Tipo de coleção inválido")
    if kind == "dinamica" and not rule:
        raise CurationError("Coleção dinâmica precisa de ao menos um filtro")
    clean_rule = Filters.from_dict(rule or {}).to_dict() if kind == "dinamica" else {}
    clean_rule.pop("colecao", None)
    try:
        with engine.begin() as conn:
            cid = conn.execute(
                text(
                    "INSERT INTO curadoria.colecao (nome, descricao, responsavel, tipo, regra_filtro) "
                    "VALUES (:n, :d, :o, :t, CAST(:r AS jsonb)) RETURNING id"
                ),
                {"n": name, "d": description, "o": owner, "t": kind, "r": json.dumps(clean_rule)},
            ).scalar_one()
    except IntegrityError as exc:
        raise CurationError(f"Já existe uma coleção chamada '{name}'") from exc
    if kind == "dinamica":
        _snapshot(engine, int(cid), first=True)
    return int(cid)


def get(engine: Engine, collection_id: int) -> dict[str, Any]:
    with engine.connect() as conn:
        r = conn.execute(
            text("SELECT * FROM curadoria.colecao WHERE id = :i"), {"i": collection_id}
        ).first()
    if r is None:
        raise NotFoundError(str(collection_id))
    return _row(r, _count(engine, collection_id))


def list_all(engine: Engine) -> list[dict[str, Any]]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM curadoria.colecao ORDER BY nome")).all()
    return [_row(r, _count(engine, r.id)) for r in rows]


def update(
    engine: Engine,
    collection_id: int,
    *,
    name: str | None = None,
    description: str | None = None,
    owner: str | None = None,
    rule: dict[str, Any] | None = None,
) -> None:
    current = get(engine, collection_id)
    new_rule = current["regra_filtro"]
    if rule is not None:
        if current["tipo"] != "dinamica":
            raise CurationError("Só coleções dinâmicas têm regra de filtro")
        new_rule = Filters.from_dict(rule).to_dict()
        new_rule.pop("colecao", None)
    try:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE curadoria.colecao SET nome = :n, descricao = :d, responsavel = :o, "
                    "regra_filtro = CAST(:r AS jsonb) WHERE id = :i"
                ),
                {
                    "n": (name or current["nome"]).strip(),
                    "d": description if description is not None else current["descricao"],
                    "o": owner if owner is not None else current["responsavel"],
                    "r": json.dumps(new_rule),
                    "i": collection_id,
                },
            )
    except IntegrityError as exc:
        raise CurationError("Já existe uma coleção com esse nome") from exc


def delete(engine: Engine, collection_id: int) -> None:
    with engine.begin() as conn:
        if (
            conn.execute(
                text("DELETE FROM curadoria.colecao WHERE id = :i"), {"i": collection_id}
            ).rowcount
            == 0
        ):
            raise NotFoundError(str(collection_id))


def add_items(engine: Engine, collection_id: int, ids: list[str], mode: str = "incluir") -> int:
    if mode not in ("incluir", "excluir"):
        raise CurationError("Modo inválido")
    col = get(engine, collection_id)
    if col["tipo"] == "manual" and mode == "excluir":
        raise CurationError("Coleções manuais não têm exceções; remova o item")
    with engine.begin() as conn:
        found = [
            r.id
            for r in conn.execute(
                text("SELECT id FROM catalogo.conjunto WHERE id = ANY(:i)"), {"i": ids}
            )
        ]
        if found:
            conn.execute(
                text(
                    "INSERT INTO curadoria.colecao_item (colecao_id, conjunto_id, modo) VALUES (:c, :i, :m) "
                    "ON CONFLICT (colecao_id, conjunto_id) DO UPDATE SET modo = EXCLUDED.modo"
                ),
                [{"c": collection_id, "i": i, "m": mode} for i in found],
            )
    return len(found)


def remove_items(engine: Engine, collection_id: int, ids: list[str]) -> int:
    get(engine, collection_id)
    with engine.begin() as conn:
        return conn.execute(
            text(
                "DELETE FROM curadoria.colecao_item WHERE colecao_id = :c AND conjunto_id = ANY(:i)"
            ),
            {"c": collection_id, "i": ids},
        ).rowcount


def add_by_filter(engine: Engine, collection_id: int, filters: Filters) -> int:
    """Adiciona à coleção todos os conjuntos que a busca atual devolve (US-033)."""
    ids = SearchService(engine).ids(filters)
    return add_items(engine, collection_id, ids)


def members(engine: Engine, collection_id: int) -> list[str]:
    get(engine, collection_id)
    return SearchService(engine).ids(Filters(colecao=collection_id))


def _snapshot(engine: Engine, collection_id: int, *, first: bool = False) -> None:
    """Compara os membros atuais com os da última extração e guarda quem entrou e quem saiu."""
    now_ids = SearchService(engine).ids(Filters(colecao=collection_id))
    with engine.begin() as conn:
        prev = conn.execute(
            text("SELECT ultimos_membros FROM curadoria.colecao WHERE id = :i"),
            {"i": collection_id},
        ).scalar_one_or_none()
        if prev is None:
            return
        before = set(prev or [])
        diff = (
            None
            if first
            else {
                "entraram": sorted(set(now_ids) - before),
                "sairam": sorted(before - set(now_ids)),
            }
        )
        conn.execute(
            text(
                "UPDATE curadoria.colecao SET ultimos_membros = :m, ultimo_diff = CAST(:d AS jsonb) WHERE id = :i"
            ),
            {"m": now_ids, "d": json.dumps(diff) if diff is not None else None, "i": collection_id},
        )


def refresh_snapshots(engine: Engine) -> int:
    """Chamado ao fim de cada extração: registra o que entrou e saiu de cada coleção dinâmica."""
    with engine.connect() as conn:
        ids = [
            r.id
            for r in conn.execute(text("SELECT id FROM curadoria.colecao WHERE tipo = 'dinamica'"))
        ]
    for cid in ids:
        _snapshot(engine, cid)
    return len(ids)
