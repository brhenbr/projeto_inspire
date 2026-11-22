"""Chat em linguagem natural: o LLM traduz o pedido em filtros; a busca existente executa (ADR-0016)."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from inspire.api.deps import get_db
from inspire.config import Settings, get_settings
from inspire.llm import interpret, providers

router = APIRouter(prefix="/chat", tags=["chat"])
Db = Annotated[Engine, Depends(get_db)]
Cfg = Annotated[Settings, Depends(get_settings)]


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=2, max_length=interpret.MAX_TEXT)
    tamanho: int = Field(default=10, ge=1, le=50)


@router.post("/perguntar")
def perguntar(body: Pergunta, db: Db, cfg: Cfg) -> dict[str, Any]:
    """Interpreta o pedido, mostra os filtros usados e devolve os primeiros resultados."""
    try:
        provider = providers.build_provider(cfg)
    except providers.LlmDisabledError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    try:
        result = interpret.interpret(db, provider, body.pergunta)
    except providers.LlmError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    found, used, removed = interpret.search_relaxed(db, result.filtros, size=body.tamanho)
    found.pop("facetas", None)
    info = provider.info
    return {
        "pergunta": body.pergunta,
        "filtros": used,
        "filtros_pedidos": result.filtros,
        "filtros_removidos": removed,
        "explicacao": result.explicacao,
        "ignorados": result.ignorados,
        "organizacao": result.organizacao,
        "provedor": {
            "nome": info.nome,
            "modelo": info.modelo,
            "externo": info.externo,
            "simulado": info.simulado,
        },
        "resultado": found,
    }
