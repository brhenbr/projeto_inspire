"""Dependências compartilhadas das rotas (substituíveis nos testes)."""

from datetime import timedelta

from sqlalchemy import Engine

from inspire.config import get_settings
from inspire.db import get_engine
from inspire.extraction.control import Policy


def get_db() -> Engine:
    return get_engine()


def get_policy() -> Policy:
    s = get_settings()
    return Policy(
        min_incremental=timedelta(minutes=s.extraction_min_interval_incremental_min),
        min_full=timedelta(minutes=s.extraction_min_interval_full_min),
        failure_wait=timedelta(minutes=s.extraction_failure_wait_min),
    )
