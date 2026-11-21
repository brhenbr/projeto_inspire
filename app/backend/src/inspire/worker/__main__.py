"""Processo worker. Por ora só mantém o processo vivo; a fila de jobs entra com a extração."""

import signal
import threading
from types import FrameType

import structlog

from inspire import __version__
from inspire.config import get_settings
from inspire.db import database_is_up
from inspire.logging import configure_logging

HEARTBEAT_SECONDS = 30


def run(stop: threading.Event, heartbeat_seconds: float = HEARTBEAT_SECONDS) -> None:
    log = structlog.get_logger("worker")
    log.info("worker_iniciado", versao=__version__)
    while not stop.is_set():
        log.info("worker_batimento", banco_ok=database_is_up())
        stop.wait(heartbeat_seconds)
    log.info("worker_encerrado")


def main() -> None:
    configure_logging(get_settings().log_level)
    stop = threading.Event()

    def _handle(_signum: int, _frame: FrameType | None) -> None:
        stop.set()

    signal.signal(signal.SIGTERM, _handle)
    signal.signal(signal.SIGINT, _handle)
    run(stop)


if __name__ == "__main__":
    main()
