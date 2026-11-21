"""Qualidade: regras configuráveis e recálculo (ADR-0009)."""

import threading
from datetime import UTC, datetime
from typing import Annotated, Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import Engine, text

from inspire.api.deps import get_db
from inspire.quality import service

router = APIRouter(prefix="/qualidade", tags=["qualidade"])
Db = Annotated[Engine, Depends(get_db)]

_lock = threading.Lock()
_state: dict[str, Any] = {
    "em_andamento": False,
    "iniciado_em": None,
    "finalizado_em": None,
    "pontuados": None,
    "erro": None,
}


class RegraEdicao(BaseModel):
    peso: float | None = Field(default=None, ge=0, le=10)
    ativa: bool | None = None


@router.get("/regras")
def regras(db: Db) -> list[dict[str, Any]]:
    service.seed_rules(db)
    with db.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT chave, dimensao, framework, nome, descricao, peso, fonte, ativa "
                "FROM analitico.regra_qualidade ORDER BY chave"
            )
        ).all()
    return [{**r._mapping, "peso": float(r.peso)} for r in rows]


@router.put("/regras/{chave}")
def editar_regra(chave: str, edicao: RegraEdicao, db: Db) -> dict[str, Any]:
    """Altera peso e/ou ativação. Depois, chame POST /qualidade/recalcular para aplicar às notas."""
    service.seed_rules(db)
    with db.begin() as conn:
        row = conn.execute(
            text(
                "UPDATE analitico.regra_qualidade SET peso = COALESCE(:p, peso), ativa = COALESCE(:a, ativa) "
                "WHERE chave = :k RETURNING chave, peso, ativa"
            ),
            {"p": edicao.peso, "a": edicao.ativa, "k": chave},
        ).first()
    if row is None:
        raise HTTPException(status_code=404, detail="Regra não encontrada")
    return {"chave": row.chave, "peso": float(row.peso), "ativa": row.ativa}


def _run_recompute(engine: Engine) -> None:
    try:
        scored = service.recompute(engine)
        _state.update(pontuados=scored, erro=None)
    except Exception as exc:
        _state.update(erro=f"{type(exc).__name__}: {exc}")
    finally:
        _state.update(em_andamento=False, finalizado_em=datetime.now(UTC).isoformat())
        _lock.release()


@router.post("/recalcular", status_code=status.HTTP_202_ACCEPTED)
def recalcular(db: Db, tasks: BackgroundTasks) -> dict[str, Any]:
    """Recalcula a nota de todos os conjuntos em segundo plano (uma execução por vez)."""
    if not _lock.acquire(blocking=False):
        return {**_state, "mensagem": "Já há um recálculo em andamento"}
    _state.update(
        em_andamento=True, iniciado_em=datetime.now(UTC).isoformat(), finalizado_em=None, erro=None
    )
    tasks.add_task(_run_recompute, db)
    return dict(_state)


@router.get("/recalculo")
def estado_recalculo() -> dict[str, Any]:
    return dict(_state)
