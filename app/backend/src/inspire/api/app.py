"""Aplicação FastAPI. A API é versionada em /v1 e documentada em OpenAPI."""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from inspire import __version__
from inspire.api.routes import curadoria, descoberta, exportacao, extracoes, llm, qualidade, saude
from inspire.config import get_settings
from inspire.curation.service import CurationError, NotFoundError
from inspire.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(get_settings().log_level)
    app = FastAPI(
        title="Inspire Catálogo",
        version=__version__,
        description="API de extração, discovery e curadoria do catálogo do dados.gov.br.",
    )

    @app.exception_handler(CurationError)
    async def _invalid(_: Request, exc: CurationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": str(exc)})

    @app.exception_handler(NotFoundError)
    async def _missing(_: Request, exc: NotFoundError) -> JSONResponse:
        return JSONResponse(status_code=404, content={"detail": f"Não encontrado: {exc}"})

    for module in (saude, extracoes, descoberta, qualidade, curadoria, llm, exportacao):
        app.include_router(module.router, prefix="/v1")
    return app


app = create_app()
