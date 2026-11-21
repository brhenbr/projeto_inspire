"""Configuração global dos testes.

Os testes de integração NUNCA usam o banco da aplicação: rodam em `<banco>_test`, criado aqui. Isso evita
poluir dados reais e impede que um worker em execução pegue jobs criados por testes.
"""

import os

import psycopg
from sqlalchemy.engine import make_url

DEFAULT_URL = "postgresql+psycopg://inspire:inspire_dev@db:5432/inspire"


def _use_test_database() -> None:
    url = make_url(os.environ.get("DATABASE_URL", DEFAULT_URL))
    name = url.database or "inspire"
    if not name.endswith("_test"):
        url = url.set(database=f"{name}_test")
    os.environ["DATABASE_URL"] = url.render_as_string(hide_password=False)
    try:
        with psycopg.connect(
            host=url.host,
            port=url.port or 5432,
            user=url.username,
            password=url.password,
            dbname="postgres",
            autocommit=True,
            connect_timeout=5,
        ) as conn:
            exists = conn.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s", (url.database,)
            ).fetchone()
            if not exists:
                conn.execute(f'CREATE DATABASE "{url.database}"')
    except psycopg.OperationalError:
        pass  # sem banco, só os testes de integração falham (e dizem por quê)


_use_test_database()
