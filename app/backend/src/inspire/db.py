"""Acesso ao PostgreSQL."""

from functools import lru_cache

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError

from inspire.config import get_settings

SCHEMAS = ("raw", "catalogo", "curadoria", "analitico")


@lru_cache
def get_engine() -> Engine:
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def database_is_up(engine: Engine | None = None) -> bool:
    """Retorna True se o banco responde a uma consulta simples."""
    try:
        with (engine or get_engine()).connect() as conn:
            conn.execute(text("SELECT 1"))
    except SQLAlchemyError:
        return False
    return True
