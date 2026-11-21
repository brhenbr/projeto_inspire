"""Reivindicação e execução de jobs (ADR-0007): as tabelas de execução são a própria fila."""

from __future__ import annotations

import structlog
from sqlalchemy import Engine, text

from inspire.config import Settings
from inspire.extraction.errors import PortalAuthError
from inspire.extraction.portal_client import PortalClient
from inspire.extraction.runner import ExtractionRunner


def requeue_interrupted(engine: Engine) -> int:
    """Ao iniciar, devolve à fila o que ficou 'em andamento' por queda do processo (retomada por fase)."""
    with engine.begin() as conn:
        return conn.execute(
            text("UPDATE raw.execucao SET estado = 'enfileirada' WHERE estado = 'em_andamento'")
        ).rowcount


def claim_next_extraction(engine: Engine) -> int | None:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id FROM raw.execucao WHERE estado = 'enfileirada' ORDER BY id "
                "LIMIT 1 FOR UPDATE SKIP LOCKED"
            )
        ).first()
        if row is None:
            return None
        conn.execute(
            text(
                "UPDATE raw.execucao SET estado = 'em_andamento', iniciada_em = COALESCE(iniciada_em, now()), "
                "batimento_em = now() WHERE id = :r"
            ),
            {"r": row.id},
        )
        return int(row.id)


def process_next(engine: Engine, settings: Settings, *, after_extraction=None) -> bool:  # type: ignore[no-untyped-def]
    """Executa o próximo job pendente. Devolve True se havia algo a fazer."""
    log = structlog.get_logger("worker")
    run_id = claim_next_extraction(engine)
    if run_id is None:
        return False
    log.info("job_iniciado", tipo="extracao", execucao=run_id)
    try:
        client = PortalClient(
            settings.dados_gov_base_url,
            settings.dados_gov_api_key.get_secret_value(),
            max_retries=settings.portal_max_retries,
            empty_retries=settings.portal_empty_retries,
            backoff_base_s=settings.portal_backoff_base_s,
            backoff_cap_s=settings.portal_backoff_cap_s,
            max_concurrency=settings.portal_max_concurrency,
            connect_timeout_s=settings.portal_connect_timeout_s,
            read_timeout_s=settings.portal_read_timeout_s,
            max_rps=settings.portal_max_rps,
            throttle_cooldown_s=settings.portal_throttle_cooldown_s,
            throttle_cap_s=settings.portal_throttle_cap_s,
        )
    except PortalAuthError as exc:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE raw.execucao SET estado = 'falhou', finalizada_em = now(), erro = :e WHERE id = :r"
                ),
                {"e": str(exc), "r": run_id},
            )
        return True
    with client:
        ExtractionRunner(
            engine,
            client,
            concurrency=settings.portal_max_concurrency,
            on_finished=after_extraction,
        ).run(run_id)
    return True
