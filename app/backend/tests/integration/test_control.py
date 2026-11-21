from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import Engine, text

from inspire.extraction import control
from inspire.extraction.control import Policy
from inspire.worker import jobs

pytestmark = pytest.mark.integration
NOW = datetime(2026, 11, 21, 12, 0, tzinfo=UTC)


def insert_run(
    db: Engine, kind: str, state: str, started: datetime, finished: datetime | None = None
) -> int:
    with db.begin() as conn:
        return int(
            conn.execute(
                text(
                    "INSERT INTO raw.execucao (tipo, estado, criada_em, iniciada_em, finalizada_em) "
                    "VALUES (:t, :s, :i, :i, :f) RETURNING id"
                ),
                {"t": kind, "s": state, "i": started, "f": finished or started},
            ).scalar_one()
        )


def test_primeiro_pedido_cria_a_execucao(db: Engine) -> None:
    d = control.request_extraction(db, "incremental", now=NOW)

    assert d.status == "allowed" and d.run_id is not None


def test_pedido_com_execucao_ativa_devolve_a_existente(db: Engine) -> None:
    first = control.request_extraction(db, "incremental", now=NOW)

    again = control.request_extraction(db, "completa", now=NOW)
    forced = control.request_extraction(db, "completa", forced=True, now=NOW)

    assert again.status == "existing" and again.run_id == first.run_id
    assert forced.status == "existing" and forced.run_id == first.run_id  # forçar não fura a regra


def test_incremental_dentro_do_intervalo_e_recusada_com_horario_de_liberacao(db: Engine) -> None:
    started = NOW - timedelta(minutes=20)
    insert_run(db, "incremental", "concluida", started)

    d = control.request_extraction(db, "incremental", now=NOW)

    assert d.status == "too_soon"
    assert d.available_at == started + timedelta(minutes=60)


def test_incremental_depois_do_intervalo_e_aceita(db: Engine) -> None:
    insert_run(db, "incremental", "concluida", NOW - timedelta(minutes=61))

    assert control.request_extraction(db, "incremental", now=NOW).status == "allowed"


def test_completa_tem_intervalo_maior_e_so_conta_outra_completa(db: Engine) -> None:
    insert_run(db, "incremental", "concluida", NOW - timedelta(hours=2))
    assert control.evaluate(db, "completa", now=NOW).status == "allowed"  # incremental não conta

    insert_run(db, "completa", "concluida", NOW - timedelta(hours=3))
    d = control.evaluate(db, "completa", now=NOW)
    assert d.status == "too_soon"
    assert d.available_at == NOW - timedelta(hours=3) + timedelta(hours=24)


def test_completa_recente_tambem_vale_para_a_incremental(db: Engine) -> None:
    insert_run(db, "completa", "concluida", NOW - timedelta(minutes=10))

    assert control.evaluate(db, "incremental", now=NOW).status == "too_soon"


def test_forcar_ignora_o_intervalo(db: Engine) -> None:
    insert_run(db, "incremental", "concluida", NOW - timedelta(minutes=1))

    d = control.request_extraction(db, "incremental", forced=True, requested_by="curador", now=NOW)

    assert d.status == "allowed"
    with db.connect() as conn:
        got = conn.execute(
            text("SELECT forcada, solicitada_por FROM raw.execucao WHERE id = :r"), {"r": d.run_id}
        ).one()
    assert got == (True, "curador")


def test_falha_recente_exige_espera_curta_mas_nao_inicia_o_intervalo_longo(db: Engine) -> None:
    insert_run(db, "incremental", "falhou", NOW - timedelta(minutes=2), NOW - timedelta(minutes=2))

    d = control.evaluate(db, "incremental", now=NOW)
    assert d.status == "too_soon"
    assert d.available_at == NOW - timedelta(minutes=2) + timedelta(minutes=5)

    assert control.evaluate(db, "incremental", now=NOW + timedelta(minutes=4)).status == "allowed"


def test_falha_antiga_nao_bloqueia_depois_de_um_sucesso(db: Engine) -> None:
    insert_run(db, "incremental", "falhou", NOW - timedelta(hours=5), NOW - timedelta(hours=5))
    insert_run(db, "incremental", "concluida", NOW - timedelta(hours=3))

    assert control.evaluate(db, "incremental", now=NOW).status == "allowed"


def test_politica_configuravel(db: Engine) -> None:
    insert_run(db, "incremental", "concluida", NOW - timedelta(minutes=10))

    assert (
        control.evaluate(
            db, "incremental", now=NOW, policy=Policy(min_incremental=timedelta(minutes=5))
        ).status
        == "allowed"
    )


def test_cancelar_execucao_enfileirada_e_imediato(db: Engine) -> None:
    run = control.request_extraction(db, "incremental", now=NOW).run_id
    assert run is not None

    assert control.cancel_run(db, run) == "cancelada"
    assert control.cancel_run(db, run) is None  # já não está ativa


def test_cancelar_execucao_em_andamento_apenas_solicita(db: Engine) -> None:
    run = control.request_extraction(db, "incremental", now=NOW).run_id
    assert run is not None
    assert jobs.claim_next_extraction(db) == run

    assert control.cancel_run(db, run) == "cancelamento_solicitado"


def test_worker_reivindica_uma_unica_vez_e_retoma_o_que_ficou_pendurado(db: Engine) -> None:
    run = control.request_extraction(db, "completa", now=NOW).run_id

    assert jobs.claim_next_extraction(db) == run
    assert jobs.claim_next_extraction(db) is None  # já reivindicada
    assert jobs.requeue_interrupted(db) == 1  # o worker caiu
    assert jobs.claim_next_extraction(db) == run
