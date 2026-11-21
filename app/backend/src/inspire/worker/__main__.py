"""Processo worker: consulta a fila (tabelas de execução) e executa um job por vez."""

import signal
import threading
from collections.abc import Callable
from types import FrameType

import structlog

from inspire import __version__
from inspire.analytics.pipeline import rebuild_after_extraction
from inspire.config import get_settings
from inspire.db import get_engine
from inspire.logging import configure_logging
from inspire.worker import jobs

POLL_SECONDS = 2.0


def run(
    stop: threading.Event,
    process: Callable[[], bool],
    poll_seconds: float = POLL_SECONDS,
) -> None:
    """Laço principal: processa jobs enquanto houver; dorme quando a fila estiver vazia."""
    log = structlog.get_logger("worker")
    log.info("worker_iniciado", versao=__version__)
    while not stop.is_set():
        try:
            worked = process()
        except Exception as exc:
            log.error("worker_erro", erro=type(exc).__name__)
            worked = False
        if not worked:
            stop.wait(poll_seconds)
    log.info("worker_encerrado")


def main() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    engine = get_engine()
    stop = threading.Event()

    def _handle(_signum: int, _frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    requeued = jobs.requeue_interrupted(engine)
    if requeued:
        structlog.get_logger("worker").info("execucoes_retomadas", quantidade=requeued)
    run(
        stop,
        lambda: jobs.process_next(
            engine,
            settings,
            after_extraction=lambda run_id: rebuild_after_extraction(engine, run_id),
        ),
    )


if __name__ == "__main__":
    main()
