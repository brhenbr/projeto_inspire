"""O que roda depois de cada extração bem-sucedida."""

from sqlalchemy import Engine

from inspire.curation import collections
from inspire.quality import service as quality


def rebuild_after_extraction(engine: Engine, _run_id: int | None = None) -> None:
    """Reconstrói o modelo de leitura, recalcula a qualidade e registra o que mudou nas coleções dinâmicas."""
    quality.recompute(engine)
    collections.refresh_snapshots(engine)
