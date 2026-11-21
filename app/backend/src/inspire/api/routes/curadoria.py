"""Curadoria humana: edição de campos, status de revisão, fila priorizada e coleções."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Header, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine

from inspire.api.deps import get_db
from inspire.api.routes.descoberta import get_filters
from inspire.curation import collections, service
from inspire.discovery.search import Filters, SearchService

router = APIRouter(tags=["curadoria"])
Db = Annotated[Engine, Depends(get_db)]


def get_author(x_curador: Annotated[str | None, Header()] = None) -> str:
    """Protótipo monousuário: o autor é informado por cabeçalho opcional; sem ele, 'curador'."""
    return (x_curador or "curador").strip()[:80] or "curador"


Author = Annotated[str, Depends(get_author)]


class AlteracaoPedido(BaseModel):
    campos: dict[str, Any] = Field(
        description="Campo -> novo valor. Campos: " + ", ".join(service.EDITABLE)
    )
    comentario: str | None = None


class ReversaoPedido(BaseModel):
    campo: str


class StatusPedido(BaseModel):
    estado: str
    duplicado_de: str | None = None


class LotePedido(BaseModel):
    estado: str
    ids: list[str] | None = None
    filtros: dict[str, Any] | None = None


class ColecaoNova(BaseModel):
    nome: str
    tipo: str = "manual"
    descricao: str | None = None
    responsavel: str | None = None
    regra_filtro: dict[str, Any] | None = None


class ColecaoEdicao(BaseModel):
    nome: str | None = None
    descricao: str | None = None
    responsavel: str | None = None
    regra_filtro: dict[str, Any] | None = None


class ItensPedido(BaseModel):
    ids: list[str] = Field(min_length=1, max_length=5000)
    modo: str = "incluir"


class PorBuscaPedido(BaseModel):
    filtros: dict[str, Any]


# ----------------------------------------------------------------- campos e status


@router.patch("/conjuntos/{conjunto_id}/curadoria")
def alterar(conjunto_id: str, pedido: AlteracaoPedido, db: Db, autor: Author) -> dict[str, Any]:
    """Altera campos curados. A edição fica registrada; o dado do portal nunca é sobrescrito."""
    mudou = service.apply_changes(
        db, conjunto_id, pedido.campos, author=autor, comment=pedido.comentario
    )
    return {"alterados": mudou}


@router.post("/conjuntos/{conjunto_id}/curadoria/reverter")
def reverter(conjunto_id: str, pedido: ReversaoPedido, db: Db, autor: Author) -> dict[str, Any]:
    return {"revertido": service.revert_field(db, conjunto_id, pedido.campo, author=autor)}


@router.put("/conjuntos/{conjunto_id}/status")
def mudar_status(conjunto_id: str, pedido: StatusPedido, db: Db, autor: Author) -> dict[str, str]:
    service.set_status(
        db, conjunto_id, pedido.estado, author=autor, duplicate_of=pedido.duplicado_de
    )
    return {"estado": pedido.estado}


@router.post("/curadoria/status-em-lote")
def status_em_lote(pedido: LotePedido, db: Db, autor: Author) -> dict[str, int]:
    """Muda o status de vários conjuntos, por lista de ids ou pelos filtros de uma busca."""
    if bool(pedido.ids) == bool(pedido.filtros):
        raise service.CurationError("Informe 'ids' ou 'filtros' (apenas um dos dois)")
    ids = pedido.ids or SearchService(db).ids(Filters.from_dict(pedido.filtros or {}))
    return {"alterados": service.set_status_bulk(db, ids, pedido.estado, author=autor)}


@router.get("/curadoria/fila")
def fila(
    db: Db,
    filtros: Annotated[Filters, Depends(get_filters)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=100)] = 20,
) -> dict[str, Any]:
    """Conjuntos a curar, do mais prioritário (pior qualidade e mais usado) para o menos."""
    filtros.estado_curadoria = filtros.estado_curadoria or "pendente"
    if filtros.sem_detalhe is None:
        filtros.sem_detalhe = False
    return SearchService(db).search(filtros, page=pagina, size=tamanho, sort="prioridade")


# ----------------------------------------------------------------- coleções


@router.get("/colecoes")
def listar_colecoes(db: Db) -> list[dict[str, Any]]:
    return collections.list_all(db)


@router.post("/colecoes", status_code=status.HTTP_201_CREATED)
def criar_colecao(pedido: ColecaoNova, db: Db) -> dict[str, Any]:
    cid = collections.create(
        db,
        pedido.nome,
        kind=pedido.tipo,
        description=pedido.descricao,
        owner=pedido.responsavel,
        rule=pedido.regra_filtro,
    )
    return collections.get(db, cid)


@router.get("/colecoes/{colecao_id}")
def detalhar_colecao(colecao_id: int, db: Db) -> dict[str, Any]:
    return collections.get(db, colecao_id)


@router.put("/colecoes/{colecao_id}")
def editar_colecao(colecao_id: int, pedido: ColecaoEdicao, db: Db) -> dict[str, Any]:
    collections.update(
        db,
        colecao_id,
        name=pedido.nome,
        description=pedido.descricao,
        owner=pedido.responsavel,
        rule=pedido.regra_filtro,
    )
    return collections.get(db, colecao_id)


@router.delete("/colecoes/{colecao_id}", status_code=status.HTTP_204_NO_CONTENT)
def apagar_colecao(colecao_id: int, db: Db) -> None:
    collections.delete(db, colecao_id)


@router.get("/colecoes/{colecao_id}/conjuntos")
def conjuntos_da_colecao(
    colecao_id: int,
    db: Db,
    filtros: Annotated[Filters, Depends(get_filters)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=100)] = 20,
    ordem: str = "titulo",
) -> dict[str, Any]:
    collections.get(db, colecao_id)
    filtros.colecao = colecao_id
    return SearchService(db).search(filtros, page=pagina, size=tamanho, sort=ordem)


@router.post("/colecoes/{colecao_id}/itens")
def adicionar_itens(colecao_id: int, pedido: ItensPedido, db: Db) -> dict[str, int]:
    return {"adicionados": collections.add_items(db, colecao_id, pedido.ids, pedido.modo)}


@router.post("/colecoes/{colecao_id}/itens/remover")
def remover_itens(colecao_id: int, pedido: ItensPedido, db: Db) -> dict[str, int]:
    return {"removidos": collections.remove_items(db, colecao_id, pedido.ids)}


@router.post("/colecoes/{colecao_id}/itens-por-busca")
def adicionar_por_busca(colecao_id: int, pedido: PorBuscaPedido, db: Db) -> dict[str, int]:
    """Adiciona à coleção todos os conjuntos que uma busca devolve (inclui filtros e texto)."""
    return {
        "adicionados": collections.add_by_filter(db, colecao_id, Filters.from_dict(pedido.filtros))
    }
