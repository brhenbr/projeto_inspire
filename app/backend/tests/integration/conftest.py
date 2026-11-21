from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import Engine

from inspire.db import get_engine
from inspire.extraction.raw_store import RawStore
from support.helpers import reset_database


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Garante o banco no esquema mais recente, independentemente do que rodou antes."""
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
