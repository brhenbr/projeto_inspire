import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import text

from inspire.db import SCHEMAS, database_is_up, get_engine

pytestmark = pytest.mark.integration


def _alembic() -> Config:
    return Config("alembic.ini")


def test_banco_responde() -> None:
    assert database_is_up()


def test_migracao_cria_e_remove_os_schemas() -> None:
    cfg = _alembic()
    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")

    with get_engine().connect() as conn:
        existentes = {
            r[0] for r in conn.execute(text("SELECT schema_name FROM information_schema.schemata"))
        }
        extensoes = {r[0] for r in conn.execute(text("SELECT extname FROM pg_extension"))}

    assert set(SCHEMAS) <= existentes
    assert {"unaccent", "pg_trgm"} <= extensoes

    command.downgrade(cfg, "base")
    command.upgrade(cfg, "head")  # deixa o banco pronto para os outros testes
