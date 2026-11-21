"""Orquestrador da extração: dimensões -> organizações -> listagem -> detalhes -> fechamento.

Cada fase é idempotente e a execução é retomável: a listagem vira linhas em `raw.fila_detalhe` e o
detalhe só processa o que ainda está pendente. Consulte os ADR-0005, 0006 e 0007.
"""

from __future__ import annotations

import json
import time
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import Any

import structlog
from sqlalchemy import Engine, text

from inspire.curation.service import on_source_changed
from inspire.extraction import normalizer
from inspire.extraction.errors import (
    PortalAuthError,
    PortalRequestError,
    PortalUnavailableError,
)
from inspire.extraction.portal_client import PortalClient
from inspire.extraction.privacy import find_email_like, strip_personal_data
from inspire.extraction.raw_store import RawStore

API = "/dados/api"
BASE = f"{API}/publico"
COVERAGE_MIN = (
    0.99  # abaixo disso a listagem é considerada incompleta e nada é marcado como removido
)
EMPTY_PAGES_TO_STOP = 3  # várias páginas vazias seguidas confirmam o fim (a API é intermitente)
BATCH = 200


class RunCancelledError(Exception):
    pass


class ExtractionRunner:
    def __init__(
        self,
        engine: Engine,
        client: PortalClient,
        *,
        concurrency: int = 4,
        on_finished: Callable[[int], None] | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._engine = engine
        self._client = client
        self._store = RawStore(engine)
        self._concurrency = concurrency
        self._on_finished = on_finished
        self._clock = clock
        self._log = structlog.get_logger("extracao")

    # ------------------------------------------------------------------ entrada

    def run(self, run_id: int) -> str:
        """Executa (ou retoma) a execução e devolve o estado final."""
        kind, totals = self._load(run_id)
        started = self._clock()
        try:
            self._phase_dimensions(run_id, totals)
            expected_by_org = self._phase_organizations(run_id)
            if not totals.get("listagem_ok"):
                self._phase_listing(run_id, kind, expected_by_org)
            self._phase_details(run_id)
            state = self._close(run_id, expected_by_org, started)
        except RunCancelledError:
            state = self._finish(run_id, "cancelada", started)
        except PortalAuthError as exc:
            state = self._finish(run_id, "falhou", started, erro=f"Chave recusada: {exc}")
        except Exception as exc:
            self._log.error("extracao_falhou", execucao=run_id, erro=type(exc).__name__)
            state = self._finish(run_id, "falhou", started, erro=f"{type(exc).__name__}: {exc}")
        if self._on_finished and state in {"concluida", "concluida_com_divergencias"}:
            self._on_finished(run_id)
        return state

    # ------------------------------------------------------------------ fases

    def _phase_dimensions(self, run_id: int, totals: dict[str, Any]) -> None:
        if totals.get("dimensoes_ok"):
            return
        self._check_cancel(run_id)
        themes = self._client.get_json(f"{API}/temas")
        formats = self._client.get_json(f"{BASE}/conjuntos-dados/formatos")
        legal = self._client.get_json(f"{BASE}/conjuntos-dados/observancia-legal")
        for kind, key, payload in (
            ("tema", "todos", {"itens": themes}),
            ("formato", "todos", {"itens": formats}),
            ("observancia_legal", "todos", {"itens": legal}),
        ):
            self._store.save(run_id, kind, key, payload)
        with self._engine.begin() as conn:
            normalizer.upsert_themes(
                conn, [t for t in themes if isinstance(t, dict) and t.get("name")]
            )
            normalizer.upsert_formats(conn, formats)
            normalizer.upsert_legal_basis(conn, [i for i in legal if isinstance(i, dict)])
        self._merge_totals(run_id, {"dimensoes_ok": True})

    def _phase_organizations(self, run_id: int) -> dict[str, int]:
        """Coleta as organizações (cheap) e devolve o total esperado de conjuntos por organização."""
        expected: dict[str, int] = {}
        page = 1
        empty_streak = 0
        while empty_streak < EMPTY_PAGES_TO_STOP:
            self._check_cancel(run_id)
            result = self._client.get_page(f"{BASE}/organizacao", {"pagina": page})
            if result.confirmed_empty:
                empty_streak += 1
            else:
                empty_streak = 0
                for org in result.items:
                    if not isinstance(org, dict) or not org.get("nome"):
                        continue
                    self._store.save(run_id, "organizacao", org["nome"], org)
                    expected[org["nome"]] = normalizer._int(org.get("qtdConjuntoDeDados")) or 0
                    with self._engine.begin() as conn:
                        normalizer.upsert_organization(conn, org)
            page += 1
        self._merge_totals(
            run_id, {"organizacoes": len(expected), "esperados": sum(expected.values())}
        )
        return expected

    def _phase_listing(self, run_id: int, kind: str, expected_by_org: dict[str, int]) -> None:
        known = self._known_items() if kind == "incremental" else {}
        page = 1
        empty_streak = 0
        while empty_streak < EMPTY_PAGES_TO_STOP:
            self._check_cancel(run_id)
            result = self._client.get_page(f"{BASE}/conjuntos-dados", {"pagina": page})
            if result.confirmed_empty:
                empty_streak += 1
            else:
                empty_streak = 0
                rows = []
                for item in result.items:
                    if not isinstance(item, dict) or not item.get("id"):
                        continue
                    needs_detail = self._needs_detail(kind, item, known.get(item["id"]))
                    rows.append(
                        {
                            "r": run_id,
                            "c": item["id"],
                            "resumo": json.dumps(item, ensure_ascii=False),
                            "estado": "pendente" if needs_detail else "concluido",
                            "motivo": None if needs_detail else "evitado",
                        }
                    )
                if rows:
                    with self._engine.begin() as conn:
                        conn.execute(
                            text(
                                "INSERT INTO raw.fila_detalhe (execucao_id, conjunto_id, resumo, estado, motivo) "
                                "VALUES (:r, :c, CAST(:resumo AS jsonb), :estado, :motivo) ON CONFLICT DO NOTHING"
                            ),
                            rows,
                        )
                if page % 50 == 0:
                    self._touch(run_id, {"paginas_listadas": page})
            page += 1
        with self._engine.begin() as conn:
            row = conn.execute(
                text(
                    "SELECT count(*) AS listados, count(*) FILTER (WHERE estado = 'pendente') AS pendentes "
                    "FROM raw.fila_detalhe WHERE execucao_id = :r"
                ),
                {"r": run_id},
            ).one()
        self._merge_totals(
            run_id,
            {
                "listagem_ok": True,
                "listados": row.listados,
                "detalhes_a_buscar": row.pendentes,
                "detalhes_evitados": row.listados - row.pendentes,
            },
        )

    def _phase_details(self, run_id: int) -> None:
        retried_errors = False
        last_flush = self._clock()
        while True:
            self._check_cancel(run_id)
            with self._engine.connect() as conn:
                batch = conn.execute(
                    text(
                        "SELECT conjunto_id, resumo FROM raw.fila_detalhe "
                        "WHERE execucao_id = :r AND estado = 'pendente' ORDER BY conjunto_id LIMIT :n"
                    ),
                    {"r": run_id, "n": BATCH},
                ).all()
            if not batch:
                if not retried_errors and self._requeue_errors(run_id):
                    retried_errors = True
                    continue
                return
            with ThreadPoolExecutor(max_workers=self._concurrency) as pool:
                futures = [
                    pool.submit(self._process_item, run_id, b.conjunto_id, dict(b.resumo))
                    for b in batch
                ]
                for future in futures:
                    future.result()  # PortalAuthError interrompe a execução inteira
            if self._clock() - last_flush > 5:
                self._merge_totals(run_id, {"fila": self._queue_counts(run_id)})
                last_flush = self._clock()

    def _process_item(self, run_id: int, cid: str, summary: dict[str, Any]) -> str:
        try:
            detail = self._client.get_json(f"{BASE}/conjuntos-dados/{cid}")
        except PortalRequestError as exc:
            with self._engine.begin() as conn:
                normalizer.normalize_without_detail(conn, run_id, summary)
            self._mark_item(run_id, cid, "sem_detalhe", f"HTTP {exc.status_code}")
            return "sem_detalhe"
        except PortalUnavailableError as exc:
            self._mark_item(run_id, cid, "erro", str(exc)[:200])
            return "erro"
        clean = strip_personal_data(detail)
        saved = self._store.save(run_id, "conjunto", cid, clean)
        with self._engine.begin() as conn:
            event = normalizer.normalize_conjunto(
                conn,
                run_id,
                clean,
                doc_hash=saved.hash,
                listing_change=summary.get("ultimaAlteracaoMetadados"),
            )
        if event == "alterado":
            on_source_changed(self._engine, cid)
        self._mark_item(run_id, cid, "concluido", None)
        emails = find_email_like(clean)
        if emails:
            self._merge_counter(run_id, "emails_em_texto_livre", emails)
        return event or "inalterado"

    def _close(self, run_id: int, expected_by_org: dict[str, int], started: float) -> str:
        with self._engine.begin() as conn:
            listed = conn.execute(
                text("SELECT count(*) FROM raw.fila_detalhe WHERE execucao_id = :r"), {"r": run_id}
            ).scalar_one()
            per_org = {
                r.org: r.n
                for r in conn.execute(
                    text(
                        "SELECT resumo->>'nomeOrganizacao' AS org, count(*) AS n FROM raw.fila_detalhe "
                        "WHERE execucao_id = :r GROUP BY 1"
                    ),
                    {"r": run_id},
                )
            }
            expected_total = sum(expected_by_org.values())
            coverage = (listed / expected_total) if expected_total else 1.0
            removed = 0
            if coverage >= COVERAGE_MIN:
                removed = normalizer.mark_removed(conn, run_id)
            conn.execute(
                text(
                    "UPDATE catalogo.conjunto SET ultima_vez_em = now() WHERE removido_em IS NULL AND id IN "
                    "(SELECT conjunto_id FROM raw.fila_detalhe WHERE execucao_id = :r AND estado = 'concluido')"
                ),
                {"r": run_id},
            )
            states = {
                r.estado: r.n
                for r in conn.execute(
                    text(
                        "SELECT estado, count(*) AS n FROM raw.fila_detalhe WHERE execucao_id = :r GROUP BY 1"
                    ),
                    {"r": run_id},
                )
            }
        divergences = sorted(
            (
                {"organizacao": slug, "esperado": exp, "listado": per_org.get(slug, 0)}
                for slug, exp in expected_by_org.items()
                if per_org.get(slug, 0) != exp
            ),
            key=lambda d: abs(d["esperado"] - d["listado"]),
            reverse=True,
        )[:30]
        with self._engine.connect() as conn:
            events = {
                r.evento: r.n
                for r in conn.execute(
                    text(
                        "SELECT evento, count(*) AS n FROM catalogo.conjunto_historico WHERE execucao_id = :r GROUP BY 1"
                    ),
                    {"r": run_id},
                )
            }
            fetched_ok = conn.execute(
                text(
                    "SELECT count(*) FROM raw.fila_detalhe WHERE execucao_id = :r AND estado = 'concluido' "
                    "AND motivo IS DISTINCT FROM 'evitado'"
                ),
                {"r": run_id},
            ).scalar_one()
        changed = events.get("novo", 0) + events.get("alterado", 0) + events.get("reaparecido", 0)
        extra = {
            "novos": events.get("novo", 0),
            "alterados": events.get("alterado", 0),
            "reaparecidos": events.get("reaparecido", 0),
            "inalterados": max(fetched_ok - changed, 0),
            "detalhes_evitados": states.get("concluido", 0) - fetched_ok,
            "listados": listed,
            "esperados": expected_total,
            "cobertura": round(coverage, 4),
            "removidos": removed,
            "sem_detalhe": states.get("sem_detalhe", 0),
            "erros": states.get("erro", 0),
            "divergencias_por_organizacao": divergences,
            "remocao_aplicada": coverage >= COVERAGE_MIN,
        }
        clean_run = coverage >= COVERAGE_MIN and extra["sem_detalhe"] == 0 and extra["erros"] == 0
        return self._finish(
            run_id, "concluida" if clean_run else "concluida_com_divergencias", started, extra=extra
        )

    # ------------------------------------------------------------------ apoio

    def _load(self, run_id: int) -> tuple[str, dict[str, Any]]:
        with self._engine.begin() as conn:
            row = conn.execute(
                text("SELECT tipo, totais FROM raw.execucao WHERE id = :r"), {"r": run_id}
            ).one()
            conn.execute(
                text(
                    "UPDATE raw.execucao SET estado = 'em_andamento', iniciada_em = COALESCE(iniciada_em, now()), "
                    "batimento_em = now() WHERE id = :r"
                ),
                {"r": run_id},
            )
        return row.tipo, dict(row.totais)

    def _known_items(self) -> dict[str, tuple[str | None, bool, bool]]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT id, alteracao_listagem, sem_detalhe, removido_em IS NOT NULL AS removido FROM catalogo.conjunto"
                )
            )
            return {r.id: (r.alteracao_listagem, r.sem_detalhe, r.removido) for r in rows}

    @staticmethod
    def _needs_detail(
        kind: str, item: dict[str, Any], known: tuple[str | None, bool, bool] | None
    ) -> bool:
        if kind == "completa" or known is None:
            return True
        changed, no_detail, removed = known
        return no_detail or removed or changed != item.get("ultimaAlteracaoMetadados")

    def _mark_item(self, run_id: int, cid: str, state: str, reason: str | None) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE raw.fila_detalhe SET estado = :s, motivo = :m WHERE execucao_id = :r AND conjunto_id = :c"
                ),
                {"s": state, "m": reason, "r": run_id, "c": cid},
            )

    def _requeue_errors(self, run_id: int) -> int:
        with self._engine.begin() as conn:
            return conn.execute(
                text(
                    "UPDATE raw.fila_detalhe SET estado = 'pendente' WHERE execucao_id = :r AND estado = 'erro'"
                ),
                {"r": run_id},
            ).rowcount

    def _queue_counts(self, run_id: int) -> dict[str, int]:
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT estado, count(*) AS n FROM raw.fila_detalhe WHERE execucao_id = :r GROUP BY 1"
                ),
                {"r": run_id},
            )
            return {r.estado: r.n for r in rows}

    def _check_cancel(self, run_id: int) -> None:
        with self._engine.connect() as conn:
            flag = conn.execute(
                text("SELECT cancelar_solicitado FROM raw.execucao WHERE id = :r"), {"r": run_id}
            ).scalar_one()
        if flag:
            raise RunCancelledError

    def _merge_totals(self, run_id: int, values: dict[str, Any]) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE raw.execucao SET totais = totais || CAST(:v AS jsonb), batimento_em = now() WHERE id = :r"
                ),
                {"v": json.dumps(values), "r": run_id},
            )

    _touch = _merge_totals

    def _merge_counter(self, run_id: int, key: str, n: int) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE raw.execucao SET totais = jsonb_set(totais, ARRAY[:k], "
                    "to_jsonb(COALESCE((totais->>:k)::int, 0) + :n)) WHERE id = :r"
                ),
                {"k": key, "n": n, "r": run_id},
            )

    def _finish(
        self,
        run_id: int,
        state: str,
        started: float,
        *,
        erro: str | None = None,
        extra: dict[str, Any] | None = None,
    ) -> str:
        totals = {**(extra or {}), "duracao_s": round(self._clock() - started, 1)}
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE raw.execucao SET estado = :s, finalizada_em = now(), erro = :e, "
                    "totais = totais || CAST(:t AS jsonb) WHERE id = :r"
                ),
                {"s": state, "e": erro, "t": json.dumps(totals), "r": run_id},
            )
        self._log.info(
            "extracao_finalizada",
            execucao=run_id,
            estado=state,
            **{k: v for k, v in totals.items() if isinstance(v, int | float)},
        )
        return state
