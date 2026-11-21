"""Discovery: busca de conjuntos, detalhe, organizações e painel."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import Engine

from inspire.api.deps import get_db
from inspire.discovery import catalog
from inspire.discovery.search import SORTS, Filters, SearchService

router = APIRouter(tags=["descoberta"])
Db = Annotated[Engine, Depends(get_db)]


def get_filters(
    q: Annotated[str | None, Query(description="Texto da busca")] = None,
    organizacao: str | None = None,
    esfera: str | None = None,
    uf: str | None = None,
    tema: str | None = None,
    tag: str | None = None,
    formato: str | None = None,
    licenca: str | None = None,
    periodicidade: str | None = None,
    selo: str | None = None,
    estado_curadoria: str | None = None,
    atualizado_portal: str | None = None,
    nota_min: float | None = None,
    nota_max: float | None = None,
    curado: bool | None = None,
    sem_detalhe: bool | None = None,
    incluir_removidos: bool = False,
    colecao: int | None = None,
) -> Filters:
    return Filters(
        q=q,
        organizacao=organizacao,
        esfera=esfera,
        uf=uf,
        tema=tema,
        tag=tag,
        formato=formato,
        licenca=licenca,
        periodicidade=periodicidade,
        selo=selo,
        estado_curadoria=estado_curadoria,
        atualizado_portal=atualizado_portal,
        nota_min=nota_min,
        nota_max=nota_max,
        curado=curado,
        sem_detalhe=sem_detalhe,
        incluir_removidos=incluir_removidos,
        colecao=colecao,
    )


@router.get("/conjuntos")
def buscar_conjuntos(
    db: Db,
    filtros: Annotated[Filters, Depends(get_filters)],
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=100)] = 20,
    ordem: Annotated[str, Query(description=f"Uma de: {', '.join(SORTS)}")] = "relevancia",
) -> dict[str, Any]:
    """Busca textual com filtros combináveis e contagem por faceta."""
    if ordem not in SORTS:
        raise HTTPException(status_code=422, detail=f"Ordem inválida: {ordem}")
    return SearchService(db).search(filtros, page=pagina, size=tamanho, sort=ordem)


@router.get("/conjuntos/{conjunto_id}")
def detalhar_conjunto(conjunto_id: str, db: Db) -> dict[str, Any]:
    found = catalog.get_dataset(db, conjunto_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Conjunto não encontrado")
    return found


@router.get("/organizacoes")
def listar_organizacoes(
    db: Db,
    q: str | None = None,
    esfera: str | None = None,
    pagina: Annotated[int, Query(ge=1)] = 1,
    tamanho: Annotated[int, Query(ge=1, le=100)] = 20,
    ordem: str = "conjuntos",
) -> dict[str, Any]:
    return catalog.list_organizations(db, q=q, esfera=esfera, page=pagina, size=tamanho, sort=ordem)


@router.get("/organizacoes/{slug}")
def detalhar_organizacao(slug: str, db: Db) -> dict[str, Any]:
    found = catalog.get_organization(db, slug)
    if found is None:
        raise HTTPException(status_code=404, detail="Organização não encontrada")
    return found


@router.get("/painel")
def painel(db: Db) -> dict[str, Any]:
    """Indicadores gerais do catálogo e da última extração."""
    return catalog.dashboard(db)
