"""Execuções de LLM, propostas e decisão humana (ADR-0011).

Fluxo: o curador escolhe tarefa e conjuntos -> execução enfileirada -> o worker gera PROPOSTAS (nada é
aplicado) -> o curador aprova, edita ou rejeita. Só a aprovação humana altera o catálogo (via curadoria).
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from typing import Any

import structlog
from sqlalchemy import Engine, text

from inspire.config import Settings
from inspire.curation import service as curation
from inspire.curation.service import CurationError, NotFoundError
from inspire.extraction.hashing import canonical_hash
from inspire.llm import providers, tasks
from inspire.llm.providers import LlmError, LlmProvider, LlmRequest

MAX_DATASETS_PER_RUN = 200
RAW_LIMIT = 8000


class ConflictError(Exception):
    """A proposta não pode ser decidida (já decidida ou desatualizada)."""


def create_execution(
    engine: Engine,
    settings: Settings,
    task_key: str,
    dataset_ids: list[str],
    *,
    instructions: str | None,
    requested_by: str,
) -> int:
    provider = providers.build_provider(settings)  # falha se desligado ou fora da lista aprovada
    task = tasks.TASKS_BY_KEY.get(task_key)
    if task is None:
        raise CurationError(f"Tarefa desconhecida: {task_key}")
    ids = list(dict.fromkeys(dataset_ids))
    if not ids:
        raise CurationError("Nenhum conjunto selecionado")
    if len(ids) > MAX_DATASETS_PER_RUN:
        raise CurationError(f"Selecione no máximo {MAX_DATASETS_PER_RUN} conjuntos por execução")
    tasks.seed_tasks(engine)
    with engine.begin() as conn:
        running = conn.execute(
            text(
                "SELECT id FROM curadoria.llm_execucao WHERE estado IN ('enfileirada', 'em_andamento') LIMIT 1"
            )
        ).first()
        if running:
            raise ConflictError(f"Já há uma execução de LLM em andamento (#{running.id})")
        return int(
            conn.execute(
                text(
                    "INSERT INTO curadoria.llm_execucao (tarefa_chave, tarefa_versao, estado, conjuntos, parametros, "
                    "provedor, modelo, externo, solicitada_por) VALUES (:t, :v, 'enfileirada', CAST(:c AS jsonb), "
                    "CAST(:p AS jsonb), :prov, :modelo, :ext, :por) RETURNING id"
                ),
                {
                    "t": task.chave,
                    "v": task.versao,
                    "c": json.dumps(ids),
                    "p": json.dumps(
                        {"instrucoes": (instructions or "").strip()[: tasks.MAX_INSTRUCTIONS]}
                    ),
                    "prov": provider.info.nome,
                    "modelo": provider.info.modelo,
                    "ext": provider.info.externo,
                    "por": requested_by,
                },
            ).scalar_one()
        )


def cancel_execution(engine: Engine, execution_id: int) -> str | None:
    with engine.begin() as conn:
        row = conn.execute(
            text("SELECT estado FROM curadoria.llm_execucao WHERE id = :i FOR UPDATE"),
            {"i": execution_id},
        ).first()
        if row is None or row.estado not in ("enfileirada", "em_andamento"):
            return None
        if row.estado == "enfileirada":
            conn.execute(
                text(
                    "UPDATE curadoria.llm_execucao SET estado = 'cancelada', finalizada_em = now() WHERE id = :i"
                ),
                {"i": execution_id},
            )
            return "cancelada"
        conn.execute(
            text("UPDATE curadoria.llm_execucao SET cancelar_solicitado = true WHERE id = :i"),
            {"i": execution_id},
        )
        return "cancelamento_solicitado"


def claim_next(engine: Engine) -> int | None:
    with engine.begin() as conn:
        row = conn.execute(
            text(
                "SELECT id FROM curadoria.llm_execucao WHERE estado = 'enfileirada' ORDER BY id "
                "LIMIT 1 FOR UPDATE SKIP LOCKED"
            )
        ).first()
        if row is None:
            return None
        conn.execute(
            text(
                "UPDATE curadoria.llm_execucao SET estado = 'em_andamento', iniciada_em = now() WHERE id = :i"
            ),
            {"i": row.id},
        )
        return int(row.id)


def requeue_interrupted(engine: Engine) -> int:
    with engine.begin() as conn:
        return conn.execute(
            text(
                "UPDATE curadoria.llm_execucao SET estado = 'enfileirada' WHERE estado = 'em_andamento'"
            )
        ).rowcount


def run_execution(
    engine: Engine,
    provider: LlmProvider,
    execution_id: int,
    *,
    interval_s: float = 0.0,
    sleep: Callable[[float], None] = time.sleep,
) -> str:
    """Gera uma proposta por conjunto. Nunca altera o catálogo."""
    log = structlog.get_logger("llm")
    with engine.connect() as conn:
        ex = conn.execute(
            text(
                "SELECT tarefa_chave, conjuntos, parametros FROM curadoria.llm_execucao WHERE id = :i"
            ),
            {"i": execution_id},
        ).one()
    task = tasks.TASKS_BY_KEY[ex.tarefa_chave]
    instructions = (ex.parametros or {}).get("instrucoes")
    themes = tasks.theme_options(engine)
    valid_themes = {t["slug"] for t in themes}
    counts = {"propostas": 0, "sem_mudanca": 0, "erros": 0, "processados": 0}
    state = "concluida"
    for dataset_id in ex.conjuntos:
        if _cancel_requested(engine, execution_id):
            state = "cancelada"
            break
        outcome = _propose(
            engine, provider, execution_id, task, dataset_id, instructions, themes, valid_themes
        )
        counts[outcome] += 1
        counts["processados"] += 1
        _save_totals(engine, execution_id, counts)
        if interval_s and provider.info.externo:
            sleep(interval_s)  # boas maneiras com a cota gratuita do provedor
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE curadoria.llm_execucao SET estado = :s, finalizada_em = now(), totais = CAST(:t AS jsonb) "
                "WHERE id = :i"
            ),
            {"s": state, "t": json.dumps(counts), "i": execution_id},
        )
    log.info("llm_execucao_finalizada", execucao=execution_id, estado=state, **counts)
    return state


def _cancel_requested(engine: Engine, execution_id: int) -> bool:
    with engine.connect() as conn:
        return bool(
            conn.execute(
                text("SELECT cancelar_solicitado FROM curadoria.llm_execucao WHERE id = :i"),
                {"i": execution_id},
            ).scalar_one()
        )


def _save_totals(engine: Engine, execution_id: int, counts: dict[str, int]) -> None:
    with engine.begin() as conn:
        conn.execute(
            text("UPDATE curadoria.llm_execucao SET totais = CAST(:t AS jsonb) WHERE id = :i"),
            {"t": json.dumps(counts), "i": execution_id},
        )


def _propose(
    engine: Engine,
    provider: LlmProvider,
    execution_id: int,
    task: tasks.TaskDef,
    dataset_id: str,
    instructions: str | None,
    themes: list[dict[str, str]],
    valid_themes: set[str],
) -> str:
    ctx = tasks.build_context(engine, dataset_id)
    if ctx is None:
        return _record(
            engine,
            execution_id,
            dataset_id,
            task,
            None,
            None,
            None,
            None,
            None,
            "Conjunto indisponível (removido ou sem detalhe)",
        )
    if task.chave == "sugerir-tema":
        ctx = {**ctx, "temas_disponiveis": themes}
    original = ctx[task.campo_alvo]
    system, user = tasks.render(task, ctx, instructions)
    prompt = f"[sistema]\n{system}\n\n[usuário]\n{user}"
    try:
        response = provider.complete(
            LlmRequest(system=system, user=user, task=task.chave, context=ctx)
        )
    except LlmError as exc:
        return _record(
            engine, execution_id, dataset_id, task, original, None, prompt, None, None, str(exc)
        )
    try:
        proposed = tasks.parse_output(task.chave, response.text, ctx, valid_themes)
    except ValueError as exc:
        return _record(
            engine,
            execution_id,
            dataset_id,
            task,
            original,
            None,
            prompt,
            response.text,
            None,
            str(exc),
        )
    if _same(proposed, original):
        return "sem_mudanca"
    return _record(
        engine,
        execution_id,
        dataset_id,
        task,
        original,
        proposed,
        prompt,
        response.text,
        canonical_hash(original),
        None,
        f"{response.provider}/{response.model}" if response.provider else response.model,
    )


def _same(a: Any, b: Any) -> bool:
    return (sorted(a) == sorted(b)) if isinstance(a, list) and isinstance(b, list) else a == b


def _record(
    engine: Engine,
    execution_id: int,
    dataset_id: str,
    task: tasks.TaskDef,
    original: Any,
    proposed: Any,
    prompt: str | None,
    raw: str | None,
    base_hash: str | None,
    error: str | None,
    answered_by: str | None = None,
) -> str:
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO curadoria.llm_proposta (execucao_id, conjunto_id, campo, valor_original, valor_proposto, "
                "estado, hash_base, prompt, resposta_bruta, erro, provedor) VALUES (:e, :c, :f, CAST(:o AS jsonb), CAST(:p AS jsonb), "
                ":s, :h, :pr, :r, :er, :pv)"
            ),
            {
                "e": execution_id,
                "c": dataset_id,
                "f": task.campo_alvo,
                "o": json.dumps(original, ensure_ascii=False) if original is not None else None,
                "p": json.dumps(proposed, ensure_ascii=False) if proposed is not None else None,
                "s": "erro" if error else "pendente",
                "h": base_hash,
                "pr": prompt,
                "r": (raw or "")[:RAW_LIMIT] or None,
                "er": error,
                "pv": answered_by,
            },
        )
    return "erros" if error else "propostas"


# ----------------------------------------------------------------- decisão humana


def decide(
    engine: Engine, proposal_id: int, decision: str, *, author: str, edited_value: Any = None
) -> dict[str, Any]:
    """Aprova, edita ou rejeita uma proposta. É o único caminho de uma proposta chegar ao catálogo."""
    if decision not in ("aprovar", "editar", "rejeitar"):
        raise CurationError("Decisão inválida (use aprovar, editar ou rejeitar)")
    with engine.begin() as conn:
        p = conn.execute(
            text("SELECT * FROM curadoria.llm_proposta WHERE id = :i FOR UPDATE"),
            {"i": proposal_id},
        ).first()
        if p is None:
            raise NotFoundError(f"proposta {proposal_id}")
        if p.estado != "pendente":
            raise ConflictError(f"A proposta está '{p.estado}' e não pode mais ser decidida")
        if decision == "rejeitar":
            conn.execute(
                text(
                    "UPDATE curadoria.llm_proposta SET estado = 'rejeitada', decidida_em = now(), decidida_por = :a WHERE id = :i"
                ),
                {"a": author, "i": proposal_id},
            )
            return {"estado": "rejeitada"}
        current = conn.execute(
            text(f"SELECT {_COLUMN[p.campo]} AS v FROM analitico.conjunto_busca WHERE id = :c"),  # noqa: S608
            {"c": p.conjunto_id},
        ).scalar_one_or_none()
        stale = not _same(current, p.valor_original)
        if stale:
            conn.execute(
                text("UPDATE curadoria.llm_proposta SET estado = 'desatualizada' WHERE id = :i"),
                {"i": proposal_id},
            )
    if stale:  # a marcação já foi confirmada; só então avisamos o chamador
        raise ConflictError("O conjunto mudou depois da proposta; ela ficou desatualizada")
    if decision == "editar":
        if edited_value is None:
            raise CurationError("Informe o valor editado")
        value, state, origin = edited_value, "editada", "humano"
    else:
        value, state, origin = p.valor_proposto, "aprovada", "llm"
    curation.apply_changes(
        engine,
        p.conjunto_id,
        {p.campo: value},
        author=author,
        origin=origin,
        proposal_id=proposal_id,
        comment=f"Proposta de LLM #{proposal_id} ({state})",
    )
    with engine.begin() as conn:
        conn.execute(
            text(
                "UPDATE curadoria.llm_proposta SET estado = :s, valor_final = CAST(:v AS jsonb), decidida_em = now(), "
                "decidida_por = :a WHERE id = :i"
            ),
            {"s": state, "v": json.dumps(value, ensure_ascii=False), "a": author, "i": proposal_id},
        )
    return {"estado": state}


_COLUMN = {"descricao": "descricao", "tags": "tags", "temas": "temas", "titulo": "titulo"}


def decide_bulk(
    engine: Engine, ids: list[str] | list[int], decision: str, *, author: str
) -> dict[str, int]:
    if decision not in ("aprovar", "rejeitar"):
        raise CurationError("Em lote só é possível aprovar ou rejeitar (editar é um a um)")
    result = {"decididas": 0, "ignoradas": 0}
    for proposal_id in ids:
        try:
            decide(engine, int(proposal_id), decision, author=author)
            result["decididas"] += 1
        except (ConflictError, NotFoundError):
            result["ignoradas"] += 1
    return result


def process_next(engine: Engine, settings: Settings) -> bool:
    """Executa a próxima execução de LLM pendente (usado pelo worker)."""
    execution_id = claim_next(engine)
    if execution_id is None:
        return False
    try:
        provider = providers.build_provider(settings)
    except providers.LlmDisabledError as exc:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE curadoria.llm_execucao SET estado = 'falhou', finalizada_em = now(), erro = :e WHERE id = :i"
                ),
                {"e": str(exc), "i": execution_id},
            )
        return True
    try:
        run_execution(engine, provider, execution_id, interval_s=settings.llm_request_interval_s)
    except Exception as exc:
        with engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE curadoria.llm_execucao SET estado = 'falhou', finalizada_em = now(), erro = :e WHERE id = :i"
                ),
                {"e": f"{type(exc).__name__}: {exc}"[:500], "i": execution_id},
            )
    return True
