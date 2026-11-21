"""Aplicação FastAPI. A API é versionada em /v1 e documentada em OpenAPI."""

from fastapi import FastAPI

from inspire import __version__
from inspire.api.routes import saude
from inspire.config import get_settings
from inspire.logging import configure_logging


def create_app() -> FastAPI:
    configure_logging(get_settings().log_level)
    app = FastAPI(
        title="Inspire Catálogo",
        version=__version__,
        description="API de extração, discovery e curadoria do catálogo do dados.gov.br.",
    )
    app.include_router(saude.router, prefix="/v1")
    return app


app = create_app()
