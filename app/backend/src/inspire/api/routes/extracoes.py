"""Extrações: pedir, acompanhar e cancelar. As regras de custo ficam no backend (ADR-0006)."""

from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import Engine, text

from inspire.api.deps import get_db, get_policy
from inspire.extraction import control
from inspire.extraction.control import Policy

router = APIRouter(prefix="/extracoes", tags=["extracoes"])
Db = Annotated[Engine, Depends(get_db)]
Pol = Annotated[Policy, Depends(get_policy)]


class Pedido(BaseModel):
    tipo: Literal["incremental", "completa"] = "incremental"
    forcar: bool = False


class Extracao(BaseModel):
    id: int
    tipo: str
    estado: str
    forcada: bool
    solicitada_por: str | None
    criada_em: datetime
    iniciada_em: datetime | None
    finalizada_em: datetime | None
    cancelamento_solicitado: bool
    totais: dict[str, Any]
    erro: str | None


class Disponibilidade(BaseModel):
    pode_pedir: bool
    motivo: str | None = None
    disponivel_em: datetime | None = None


class Estado(BaseModel):
    ativa: Extracao | None
    incremental: Disponibilidade
    completa: Disponibilidade
    ultima_completa_em: datetime | None
    dias_desde_ultima_completa: int | None
    sugerir_completa: bool


_SELECT_BY_ID = text(
    "SELECT id, tipo, estado, forcada, solicitada_por, criada_em, iniciada_em, finalizada_em, cancelar_solicitado AS cancelamento_solicitado, totais, erro FROM raw.execucao WHERE id = :r"
)
_SELECT_LATEST = text(
    "SELECT id, tipo, estado, forcada, solicitada_por, criada_em, iniciada_em, finalizada_em, cancelar_solicitado AS cancelamento_solicitado, totais, erro FROM raw.execucao ORDER BY id DESC LIMIT :n"
)


_SELECT_BY_ID = text(
    "SELECT id, tipo, estado, forcada, solicitada_por, criada_em, iniciada_em, finalizada_em, cancelar_solicitado AS cancelamento_solicitado, totais, erro FROM raw.execucao WHERE id = :r"
)
_SELECT_LATEST = text(
    "SELECT id, tipo, estado, forcada, solicitada_por, criada_em, iniciada_em, finalizada_em, cancelar_solicitado AS cancelamento_solicitado, totais, erro FROM raw.execucao ORDER BY id DESC LIMIT :n"
)


def _fetch(engine: Engine, run_id: int) -> Extracao | None:
    with engine.connect() as conn:
        row = conn.execute(_SELECT_BY_ID, {"r": run_id}).first()
    return None if row is None else Extracao(**row._mapping)


@router.post("", response_model=Extracao, status_code=status.HTTP_202_ACCEPTED)
def pedir_extracao(pedido: Pedido, response: Response, db: Db, policy: Pol) -> Any:
    """202 = nova extração; 200 = já havia uma em curso (devolve a existente); 429 = dentro do intervalo."""
    decision = control.request_extraction(
        db, pedido.tipo, forced=pedido.forcar, requested_by="local", policy=policy
    )
    if decision.status == "too_soon":
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "motivo": decision.reason,
                "disponivel_em": decision.available_at.isoformat()
                if decision.available_at
                else None,
            },
        )
    if decision.status == "existing":
        response.status_code = status.HTTP_200_OK
    if decision.run_id is None:
        raise HTTPException(status_code=500, detail="Extração sem identificador")
    return _fetch(db, decision.run_id)


@router.get("/estado", response_model=Estado)
def estado(db: Db, policy: Pol) -> Estado:
    """Tudo que a tela precisa para desenhar o botão: o que pode ser pedido agora e por que não."""
    now = datetime.now(UTC)

    def disp(kind: control.Kind) -> Disponibilidade:
        d = control.evaluate(db, kind, now=now, policy=policy)
        return Disponibilidade(
            pode_pedir=d.status == "allowed", motivo=d.reason, disponivel_em=d.available_at
        )

    with db.connect() as conn:
        active = conn.execute(
            text("SELECT id FROM raw.execucao WHERE estado = ANY(:s) ORDER BY id LIMIT 1"),
            {"s": list(control.ACTIVE_STATES)},
        ).first()
        last_full = conn.execute(
            text(
                "SELECT max(COALESCE(iniciada_em, criada_em)) FROM raw.execucao "
                "WHERE tipo = 'completa' AND estado = ANY(:s)"
            ),
            {"s": list(control.SUCCESS_STATES)},
        ).scalar_one()
    days = None if last_full is None else (now - last_full).days
    return Estado(
        ativa=_fetch(db, active.id) if active else None,
        incremental=disp("incremental"),
        completa=disp("completa"),
        ultima_completa_em=last_full,
        dias_desde_ultima_completa=days,
        sugerir_completa=days is None or days >= 7,
    )


@router.get("", response_model=list[Extracao])
def listar(db: Db, limite: int = 20) -> list[Extracao]:
    with db.connect() as conn:
        rows = conn.execute(_SELECT_LATEST, {"n": max(1, min(limite, 100))})
        return [Extracao(**r._mapping) for r in rows]


@router.get("/{run_id}", response_model=Extracao)
def detalhar(run_id: int, db: Db) -> Extracao:
    found = _fetch(db, run_id)
    if found is None:
        raise HTTPException(status_code=404, detail="Extração não encontrada")
    return found


@router.post("/{run_id}/cancelar")
def cancelar(run_id: int, db: Db) -> dict[str, str]:
    result = control.cancel_run(db, run_id)
    if result is None:
        raise HTTPException(status_code=409, detail="A extração não está ativa")
    return {"resultado": result}
