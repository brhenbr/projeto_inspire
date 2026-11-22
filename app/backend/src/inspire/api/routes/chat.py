"""Chat em linguagem natural: o LLM traduz o pedido em filtros; a busca existente executa (ADR-0016)."""

import re
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from inspire.api.deps import get_db
from inspire.config import Settings, get_settings
from inspire.discovery.search import SearchService
from inspire.llm import interpret, providers

router = APIRouter(prefix="/chat", tags=["chat"])
Db = Annotated[Engine, Depends(get_db)]
Cfg = Annotated[Settings, Depends(get_settings)]


class Pergunta(BaseModel):
    pergunta: str = Field(min_length=2, max_length=interpret.MAX_TEXT)
    tamanho: int = Field(default=10, ge=1, le=50)


class PedidoColecao(BaseModel):
    descricao: str = Field(min_length=2, max_length=interpret.MAX_TEXT)


def _suggest_name(description: str, from_model: str) -> str:
    """Nome curto da coleção: o do modelo; senão, o começo da descrição até a primeira pontuação."""
    if from_model:
        return from_model[:1].upper() + from_model[1:]
    head = re.split(r"[:;,.]", description.strip(), maxsplit=1)[0]
    name = " ".join(head.split()[:8])
    return (name[:1].upper() + name[1:])[:80]


@router.post("/colecao")
def propor_colecao(body: PedidoColecao, db: Db, cfg: Cfg) -> dict[str, Any]:
    """Propõe os filtros de uma coleção dinâmica a partir de uma descrição. NÃO cria nada: quem cria é o usuário.

    Diferente do chat, não afrouxa filtros: uma coleção precisa refletir exatamente o que foi pedido.
    """
    try:
        provider = providers.build_provider(cfg)
        result = interpret.interpret(db, provider, body.descricao)
    except providers.LlmDisabledError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except providers.LlmError as exc:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
    found = SearchService(db).search(interpret.to_filters(result), size=5)
    found.pop("facetas", None)
    return {
        "nome_sugerido": _suggest_name(body.descricao, result.nome),
        "filtros": result.filtros,
        "explicacao": result.explicacao,
        "ignorados": result.ignorados,
        "organizacao": result.organizacao,
        "provedor": {
            "nome": provider.info.nome,
            "externo": provider.info.externo,
            "simulado": provider.info.simulado,
        },
        "resultado": found,
    }


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
