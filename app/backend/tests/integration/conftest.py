from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine
from sqlalchemy.engine import make_url

from inspire.config import get_settings
from inspire.db import get_engine
from inspire.extraction.raw_store import RawStore
from support.helpers import reset_database


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
