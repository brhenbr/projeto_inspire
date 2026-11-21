from collections.abc import Iterator

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from inspire.db import get_engine
from inspire.extraction.raw_store import RawStore


@pytest.fixture(scope="session", autouse=True)
def migrated_database() -> None:
    """Garante o banco no esquema mais recente, independentemente do que rodou antes."""
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def store() -> Iterator[RawStore]:
    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(
            text("TRUNCATE raw.visto, raw.documento, raw.execucao RESTART IDENTITY CASCADE")
        )
    yield RawStore(engine)
