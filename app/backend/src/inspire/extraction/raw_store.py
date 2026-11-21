"""Armazenamento da camada raw (ADR-0005). Adaptador: pode ser trocado sem tocar no resto."""

from __future__ import annotations

import json
from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from sqlalchemy import Engine, text
from sqlalchemy.exc import IntegrityError

from inspire.extraction.errors import ActiveRunExistsError
from inspire.extraction.hashing import canonical_hash
from inspire.extraction.privacy import assert_no_personal_data

ACTIVE_RUN_INDEX = "execucao_uma_ativa"


class SaveOutcome(StrEnum):
    NEW = "novo"
    CHANGED = "alterado"
    UNCHANGED = "inalterado"


@dataclass(frozen=True)
class SaveResult:
    outcome: SaveOutcome
    document_id: int
    hash: str


class RawStore:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create_run(
        self, kind: str, *, forced: bool = False, requested_by: str | None = None
    ) -> int:
        """Cria uma execução enfileirada. Falha se já houver outra ativa (garantia do banco)."""
        try:
            with self._engine.begin() as conn:
                return int(
                    conn.execute(
                        text(
                            "INSERT INTO raw.execucao (tipo, forcada, solicitada_por, estado) "
                            "VALUES (:tipo, :forcada, :por, 'enfileirada') RETURNING id"
                        ),
                        {"tipo": kind, "forcada": forced, "por": requested_by},
                    ).scalar_one()
                )
        except IntegrityError as exc:
            if ACTIVE_RUN_INDEX in str(exc.orig):
                raise ActiveRunExistsError("Já existe uma extração ativa") from exc
            raise

    def finish_run(self, run_id: int, state: str, totals: dict[str, Any] | None = None) -> None:
        with self._engine.begin() as conn:
            conn.execute(
                text(
                    "UPDATE raw.execucao SET estado = :estado, finalizada_em = now(), "
                    "totais = CAST(:totais AS jsonb) WHERE id = :id"
                ),
                {"estado": state, "totais": json.dumps(totals or {}), "id": run_id},
            )

    def save(self, run_id: int, doc_type: str, key: str, payload: dict[str, Any]) -> SaveResult:
        """Grava o documento só se o hash mudou, e registra que esta execução o viu."""
        assert_no_personal_data(payload)  # barreira final: contatos nunca chegam ao banco
        digest = canonical_hash(payload)
        with self._engine.begin() as conn:
            last = conn.execute(
                text(
                    "SELECT id, hash FROM raw.documento WHERE tipo = :tipo AND chave_externa = :chave "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"tipo": doc_type, "chave": key},
            ).first()
            if last is not None and last.hash == digest:
                outcome, doc_id = SaveOutcome.UNCHANGED, int(last.id)
            else:
                doc_id = int(
                    conn.execute(
                        text(
                            "INSERT INTO raw.documento (tipo, chave_externa, hash, payload, execucao_id) "
                            "VALUES (:tipo, :chave, :hash, CAST(:payload AS jsonb), :run) RETURNING id"
                        ),
                        {
                            "tipo": doc_type,
                            "chave": key,
                            "hash": digest,
                            "payload": json.dumps(payload, ensure_ascii=False),
                            "run": run_id,
                        },
                    ).scalar_one()
                )
                outcome = SaveOutcome.NEW if last is None else SaveOutcome.CHANGED
            conn.execute(
                text(
                    "INSERT INTO raw.visto (execucao_id, tipo, chave_externa, documento_id) "
                    "VALUES (:run, :tipo, :chave, :doc) "
                    "ON CONFLICT (execucao_id, tipo, chave_externa) DO UPDATE "
                    "SET documento_id = EXCLUDED.documento_id"
                ),
                {"run": run_id, "tipo": doc_type, "chave": key, "doc": doc_id},
            )
        return SaveResult(outcome=outcome, document_id=doc_id, hash=digest)

    def latest(self, doc_type: str, key: str) -> dict[str, Any] | None:
        with self._engine.connect() as conn:
            row = conn.execute(
                text(
                    "SELECT payload FROM raw.documento WHERE tipo = :tipo AND chave_externa = :chave "
                    "ORDER BY id DESC LIMIT 1"
                ),
                {"tipo": doc_type, "chave": key},
            ).first()
        return None if row is None else dict(row.payload)
