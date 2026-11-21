"""Exportação da base curada."""

from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import Engine

from inspire.api.deps import get_db
from inspire.api.routes.descoberta import get_filters
from inspire.curation import collections
from inspire.discovery.search import Filters
from inspire.export import service

router = APIRouter(prefix="/exportacao", tags=["exportacao"])
Db = Annotated[Engine, Depends(get_db)]
Saida = Literal["csv", "json"]  # não chamar de "formato": colide com o filtro de formato do recurso


def _stream(db: Engine, filters: Filters, fmt: Saida, name: str) -> StreamingResponse:
    items = service.rows(db, filters)
    body = service.to_csv(items) if fmt == "csv" else service.to_json(items)
    media = "text/csv; charset=utf-8" if fmt == "csv" else "application/json"
    stamp = datetime.now(UTC).strftime("%Y%m%d")
    return StreamingResponse(
        body,
        media_type=media,
        headers={"Content-Disposition": f'attachment; filename="{name}-{stamp}.{fmt}"'},
    )


@router.get("/conjuntos")
def exportar_conjuntos(
    db: Db,
    filtros: Annotated[Filters, Depends(get_filters)],
    saida: Annotated[Saida, Query()] = "csv",
) -> StreamingResponse:
    """Exporta o resultado de uma busca (com ou sem filtros): original, curado e status."""
    return _stream(db, filtros, saida, "catalogo-curado")


@router.get("/colecoes/{colecao_id}")
def exportar_colecao(
    colecao_id: int, db: Db, saida: Annotated[Saida, Query()] = "csv"
) -> StreamingResponse:
    collections.get(db, colecao_id)
    return _stream(db, Filters(colecao=colecao_id), saida, f"colecao-{colecao_id}")
