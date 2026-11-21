"""Controle de pedidos de extração (ADR-0006): custo e carga no portal.

A autoridade é o backend. Regras: uma execução ativa por vez (garantida pelo banco), intervalo mínimo desde
a última execução bem-sucedida, espera curta após falha, e "forçar" que só ignora o intervalo.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Literal

from sqlalchemy import Engine, text

from inspire.extraction.errors import ActiveRunExistsError
from inspire.extraction.raw_store import RawStore

ACTIVE_STATES = ("enfileirada", "em_andamento", "pausada")
SUCCESS_STATES = ("concluida", "concluida_com_divergencias")
FAILURE_STATES = ("falhou", "cancelada")
Kind = Literal["incremental", "completa"]


@dataclass(frozen=True)
class Policy:
    min_incremental: timedelta = timedelta(minutes=60)
    min_full: timedelta = timedelta(hours=24)
    failure_wait: timedelta = timedelta(minutes=5)


@dataclass(frozen=True)
class Decision:
    status: Literal["allowed", "existing", "too_soon"]
    run_id: int | None = None
    available_at: datetime | None = None
    reason: str | None = None


def _active_run(engine: Engine) -> int | None:
    with engine.connect() as conn:
        row = conn.execute(
            text("SELECT id FROM raw.execucao WHERE estado = ANY(:s) ORDER BY id LIMIT 1"),
            {"s": list(ACTIVE_STATES)},
        ).first()
    return None if row is None else int(row.id)


def evaluate(
    engine: Engine,
    kind: Kind,
    *,
    forced: bool = False,
    now: datetime | None = None,
    policy: Policy = Policy(),
) -> Decision:
    """Diz o que aconteceria com um pedido agora, sem criar nada."""
    now = now or datetime.now(UTC)
    active = _active_run(engine)
    if active is not None:
        return Decision("existing", run_id=active, reason="Já existe uma extração em andamento")
    if forced:
        return Decision("allowed")

    gap = policy.min_full if kind == "completa" else policy.min_incremental
    kinds = ["completa"] if kind == "completa" else ["completa", "incremental"]
    with engine.connect() as conn:
        last_ok = conn.execute(
            text(
                "SELECT max(COALESCE(iniciada_em, criada_em)) FROM raw.execucao "
                "WHERE estado = ANY(:s) AND tipo = ANY(:k)"
            ),
            {"s": list(SUCCESS_STATES), "k": kinds},
        ).scalar_one()
        last_fail = conn.execute(
            text(
                "SELECT max(COALESCE(finalizada_em, criada_em)) FROM raw.execucao WHERE estado = ANY(:s)"
            ),
            {"s": list(FAILURE_STATES)},
        ).scalar_one()

    waits: list[tuple[datetime, str]] = []
    if last_ok is not None and now < last_ok + gap:
        waits.append((last_ok + gap, "Intervalo mínimo desde a última extração bem-sucedida"))
    # a espera após falha só vale se a falha for mais recente que o último sucesso
    if (
        last_fail is not None
        and now < last_fail + policy.failure_wait
        and (last_ok is None or last_fail > last_ok)
    ):
        waits.append((last_fail + policy.failure_wait, "Espera curta depois de uma falha"))
    if waits:
        available_at, reason = max(waits)
        return Decision("too_soon", available_at=available_at, reason=reason)
    return Decision("allowed")


def request_extraction(
    engine: Engine,
    kind: Kind,
    *,
    forced: bool = False,
    requested_by: str | None = None,
    now: datetime | None = None,
    policy: Policy = Policy(),
) -> Decision:
    """Cria uma execução se as regras permitirem; senão devolve a existente ou o motivo da recusa."""
    decision = evaluate(engine, kind, forced=forced, now=now, policy=policy)
    if decision.status != "allowed":
        return decision
    try:
        run_id = RawStore(engine).create_run(kind, forced=forced, requested_by=requested_by)
    except ActiveRunExistsError:  # pedido simultâneo venceu a corrida
        return Decision(
            "existing", run_id=_active_run(engine), reason="Já existe uma extração em andamento"
        )
    return Decision("allowed", run_id=run_id)


def cancel_run(engine: Engine, run_id: int) -> str | None:
    """Cancela uma execução ativa. Devolve o novo estado, ou None se não havia o que cancelar."""
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT estado FROM raw.execucao WHERE id = :r FOR UPDATE"), {"r": run_id}
        ).first()
        if row is None or row.estado not in ACTIVE_STATES:
            return None
        if row.estado == "enfileirada":
            conn.execute(
                text(
                    "UPDATE raw.execucao SET estado = 'cancelada', finalizada_em = now() WHERE id = :r"
                ),
                {"r": run_id},
            )
            return "cancelada"
        conn.execute(
            text("UPDATE raw.execucao SET cancelar_solicitado = true WHERE id = :r"), {"r": run_id}
        )
        return "cancelamento_solicitado"
