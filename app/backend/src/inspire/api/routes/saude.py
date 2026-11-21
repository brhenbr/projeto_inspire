"""Verificação de saúde do sistema."""

from collections.abc import Callable
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Response, status
from pydantic import BaseModel

from inspire import __version__
from inspire.db import database_is_up

router = APIRouter(tags=["saude"])


class Saude(BaseModel):
    status: Literal["ok", "degradado"]
    banco: Literal["ok", "indisponivel"]
    versao: str


def get_db_check() -> Callable[[], bool]:
    return database_is_up


@router.get("/saude", response_model=Saude)
def saude(
    response: Response,
    db_check: Annotated[Callable[[], bool], Depends(get_db_check)],
) -> Saude:
    """Informa se a API e o banco estão respondendo."""
    banco_ok = db_check()
    if not banco_ok:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return Saude(
        status="ok" if banco_ok else "degradado",
        banco="ok" if banco_ok else "indisponivel",
        versao=__version__,
    )
