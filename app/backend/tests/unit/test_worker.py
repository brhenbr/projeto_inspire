import threading

from inspire.worker.__main__ import run


def test_worker_para_quando_recebe_sinal(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr("inspire.worker.__main__.database_is_up", lambda: True)
    stop = threading.Event()
    stop.set()

    run(stop, heartbeat_seconds=0)  # retorna sem travar
