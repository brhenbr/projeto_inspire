"""Exporta conjuntos com o valor original, o curado e o status (US-051).

Nunca exporta contatos pessoais (eles nem existem no banco; ADR-0002). Em CSV, células que começariam com
`=`, `+`, `-` ou `@` recebem um apóstrofo, para não serem executadas como fórmula ao abrir no Excel.
"""

from __future__ import annotations

import csv
import io
import json
from collections.abc import Iterator
from typing import Any

from sqlalchemy import Engine, text

from inspire.discovery.catalog import PORTAL_DATASET_URL
from inspire.discovery.search import Filters, SearchService

FIELDS = (
    "id",
    "titulo",
    "titulo_original",
    "descricao",
    "descricao_original",
    "organizacao",
    "organizacao_slug",
    "esfera",
    "uf",
    "temas",
    "tags",
    "formatos",
    "licenca",
    "periodicidade",
    "nota_qualidade",
    "estado_curadoria",
    "curado",
    "selo_portal",
    "atualizado_portal",
    "dados_abertos",
    "qtd_recursos",
    "metadados_atualizados_em",
    "link_portal",
)
LIST_FIELDS = ("temas", "tags", "formatos")
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
CHUNK = 1000
SQL = text(
    """
    SELECT b.id, b.titulo, c.titulo AS titulo_original, b.descricao, c.descricao AS descricao_original,
           b.organizacao_titulo AS organizacao, b.organizacao_slug, b.esfera, b.uf, b.temas, b.tags, b.formatos,
           b.licenca, b.periodicidade, b.nota_qualidade, b.estado_curadoria, b.curado, b.selo_portal,
           b.atualizado_portal, b.dados_abertos, b.qtd_recursos, b.metadados_atualizados_em, c.slug
    FROM analitico.conjunto_busca b JOIN catalogo.conjunto c ON c.id = b.id
    WHERE b.id = ANY(:ids) ORDER BY b.id
    """
)


def _row(r: Any) -> dict[str, Any]:
    d = {k: getattr(r, k, None) for k in FIELDS if k != "link_portal"}
    d["nota_qualidade"] = None if r.nota_qualidade is None else float(r.nota_qualidade)
    d["metadados_atualizados_em"] = (
        r.metadados_atualizados_em.isoformat() if r.metadados_atualizados_em else None
    )
    d["link_portal"] = f"{PORTAL_DATASET_URL}{r.slug}" if r.slug else None
    return d


def rows(engine: Engine, filters: Filters, limit: int = 100000) -> Iterator[dict[str, Any]]:
    ids = SearchService(engine).ids(filters, limit=limit)
    for start in range(0, len(ids), CHUNK):
        with engine.connect() as conn:
            for r in conn.execute(SQL, {"ids": ids[start : start + CHUNK]}):
                yield _row(r)


def _safe(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        value = " | ".join(map(str, value))
    out = str(value)
    return "'" + out if out.startswith(FORMULA_PREFIXES) else out


def to_csv(items: Iterator[dict[str, Any]]) -> Iterator[bytes]:
    """CSV em UTF-8 com BOM (abre com acentos corretos no Excel), uma linha por vez."""
    buf = io.StringIO()
    writer = csv.writer(buf, lineterminator="\r\n")
    writer.writerow(FIELDS)
    yield b"\xef\xbb\xbf" + buf.getvalue().encode("utf-8")
    for item in items:
        buf.seek(0)
        buf.truncate()
        writer.writerow([_safe(item[f]) for f in FIELDS])
        yield buf.getvalue().encode("utf-8")


def to_json(items: Iterator[dict[str, Any]]) -> Iterator[bytes]:
    yield b"["
    first = True
    for item in items:
        yield (b"" if first else b",") + json.dumps(item, ensure_ascii=False).encode("utf-8")
        first = False
    yield b"]"
