import threading

from inspire.worker.__main__ import run


def test_worker_para_quando_recebe_sinal() -> None:
    stop = threading.Event()
    stop.set()

    run(stop, lambda: False, poll_seconds=0)  # retorna sem travar


def test_worker_continua_processando_enquanto_ha_jobs_e_dorme_quando_acaba() -> None:
    stop = threading.Event()
    jobs = iter([True, True, False])
    chamadas = []

    def process() -> bool:
        chamadas.append(1)
        try:
            return next(jobs)
        finally:
            if len(chamadas) == 3:
                stop.set()

    run(stop, process, poll_seconds=0)

    assert len(chamadas) == 3


def test_worker_sobrevive_a_um_job_que_explode() -> None:
    stop = threading.Event()
    chamadas = []

    def process() -> bool:
        chamadas.append(1)
        stop.set()
        raise RuntimeError("falhou")

    run(stop, process, poll_seconds=0)

    assert chamadas == [1]
