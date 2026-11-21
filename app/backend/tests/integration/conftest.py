from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from inspire.api.app import create_app
from inspire.api.deps import get_db
from inspire.config import get_settings
from inspire.db import get_engine
from inspire.extraction.raw_store import RawStore
from inspire.quality import service as quality
from support.fake_portal import FakePortal
from support.helpers import reset_database, run_extraction


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Garante o banco de TESTE no esquema mais recente. Recusa rodar em qualquer outro banco."""
    name = make_url(get_settings().database_url).database or ""
    if not name.endswith("_test"):
        pytest.exit(
            f"Recusando rodar testes de integração no banco '{name}': só bancos *_test.",
            returncode=2,
        )
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def db() -> Iterator[Engine]:
    """Banco limpo para cada teste."""
    engine = get_engine()
    reset_database(engine)
    yield engine


@pytest.fixture
def store(db: Engine) -> RawStore:
    return RawStore(db)


@pytest.fixture
def portal() -> FakePortal:
    p = FakePortal(n_datasets=60, n_orgs=3)
    p.add("ds-saude", "orgao-1", 1)
    p.update_title("ds-saude", "Saúde da População Brasileira")
    p.datasets["ds-saude"]["descricao"] = (
        "Indicadores de mortalidade e internações hospitalares por município. " * 3
    )
    return p


@pytest.fixture
def populated(db: Engine, portal: FakePortal) -> Engine:
    """Banco com o catálogo falso já extraído e pontuado (61 conjuntos, 3 organizações)."""
    run_extraction(db, portal)
    quality.recompute(db)
    return db


@pytest.fixture
def api(populated: Engine) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    yield TestClient(app)
