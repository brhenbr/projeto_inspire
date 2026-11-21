"""Cálculo e persistência da qualidade (ADR-0009)."""

from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, text

from inspire.analytics.read_model import refresh_read_model
from inspire.quality.rules import RULES, RULES_BY_KEY, Facts

RULES_VERSION = 1
CHUNK = 1000


@dataclass(frozen=True)
class QualityResult:
    score: float
    dimensions: dict[str, float]
    details: list[dict[str, Any]]


def evaluate(
    facts: Facts, now: datetime, config: dict[str, tuple[float, bool]] | None = None
) -> QualityResult:
    """Pontua um conjunto. Regras não avaliáveis ou inativas ficam fora da nota, mas aparecem no detalhe."""
    details: list[dict[str, Any]] = []
    total: dict[str, list[float]] = defaultdict(lambda: [0.0, 0.0])  # dimensão -> [pesos, pontos]
    all_w = all_p = 0.0
    for rule in RULES:
        weight, active = (config or {}).get(rule.key, (rule.weight, True))
        outcome = rule.check(facts, now)
        counted = active and outcome.evaluable and weight > 0
        details.append(
            {
                "regra": rule.key,
                "nome": rule.name,
                "dimensao": rule.dimension,
                "peso": weight,
                "ativa": active,
                "avaliavel": outcome.evaluable,
                "passou": outcome.passed if outcome.evaluable else None,
                "mensagem": outcome.message,
            }
        )
        if counted:
            total[rule.dimension][0] += weight
            all_w += weight
            if outcome.passed:
                total[rule.dimension][1] += weight
                all_p += weight
    dims = {d: round(100 * p / w, 1) for d, (w, p) in total.items() if w > 0}
    return QualityResult(round(100 * all_p / all_w, 1) if all_w else 0.0, dims, details)


def seed_rules(engine: Engine) -> None:
    """Cadastra as regras. Pesos e ativação já ajustados no banco são preservados."""
    with engine.begin() as conn:
        conn.execute(
            text(
                "INSERT INTO analitico.regra_qualidade (chave, dimensao, framework, nome, descricao, peso, fonte) "
                "VALUES (:k, :d, :f, :n, :desc, :w, :src) ON CONFLICT (chave) DO UPDATE SET "
                "dimensao = EXCLUDED.dimensao, framework = EXCLUDED.framework, nome = EXCLUDED.nome, "
                "descricao = EXCLUDED.descricao, fonte = EXCLUDED.fonte"
            ),
            [
                {
                    "k": r.key,
                    "d": r.dimension,
                    "f": r.framework,
                    "n": r.name,
                    "desc": r.description,
                    "w": r.weight,
                    "src": r.source,
                }
                for r in RULES
            ],
        )


def load_config(engine: Engine) -> dict[str, tuple[float, bool]]:
    with engine.connect() as conn:
        rows = conn.execute(text("SELECT chave, peso, ativa FROM analitico.regra_qualidade")).all()
    return {r.chave: (float(r.peso), r.ativa) for r in rows if r.chave in RULES_BY_KEY}


_FACTS_SQL = text(
    """
    SELECT b.id, b.titulo, b.descricao, b.licenca, b.periodicidade, b.tags, b.temas,
           b.atualizado_portal, b.dados_abertos,
           c.slug, c.cobertura_temporal_inicio, c.cobertura_temporal_fim, c.cobertura_espacial,
           c.tem_responsavel, c.tem_email_responsavel, c.dados_atualizados_em,
           COALESCE((SELECT jsonb_agg(jsonb_build_object('formato', r.formato, 'link', r.link,
                                                         'titulo', r.titulo, 'descricao', r.descricao))
                     FROM catalogo.recurso r WHERE r.conjunto_id = b.id), '[]'::jsonb) AS recursos
    FROM analitico.conjunto_busca b JOIN catalogo.conjunto c ON c.id = b.id
    WHERE b.id = ANY(:ids) AND NOT b.removido AND NOT b.sem_detalhe
    """
)


def recompute(engine: Engine, ids: list[str] | None = None, now: datetime | None = None) -> int:
    """Atualiza o modelo de leitura e recalcula a qualidade. Devolve quantos conjuntos foram pontuados."""
    now = now or datetime.now(UTC)
    seed_rules(engine)
    refresh_read_model(engine, ids)
    config = load_config(engine)
    if ids is None:
        with engine.connect() as conn:
            ids = [r.id for r in conn.execute(text("SELECT id FROM catalogo.conjunto"))]
    scored = 0
    for start in range(0, len(ids), CHUNK):
        chunk = ids[start : start + CHUNK]
        with engine.connect() as conn:
            rows = conn.execute(_FACTS_SQL, {"ids": chunk}).all()
            previous = {
                r.conjunto_id: float(r.nota)
                for r in conn.execute(
                    text(
                        "SELECT conjunto_id, nota FROM analitico.qualidade_conjunto WHERE conjunto_id = ANY(:ids)"
                    ),
                    {"ids": chunk},
                )
            }
        results: list[dict[str, Any]] = []
        for r in rows:
            facts = Facts(
                id=r.id,
                titulo=r.titulo or "",
                slug=r.slug,
                descricao=r.descricao,
                licenca=r.licenca,
                periodicidade=r.periodicidade,
                tags=list(r.tags or []),
                temas=list(r.temas or []),
                cobertura_temporal_inicio=r.cobertura_temporal_inicio,
                cobertura_temporal_fim=r.cobertura_temporal_fim,
                cobertura_espacial=r.cobertura_espacial,
                tem_responsavel=r.tem_responsavel,
                tem_email_responsavel=r.tem_email_responsavel,
                dados_abertos=r.dados_abertos,
                atualizado_portal=r.atualizado_portal,
                dados_atualizados_em=r.dados_atualizados_em,
                recursos=list(r.recursos or []),
            )
            result = evaluate(facts, now, config)
            results.append(
                {
                    "id": r.id,
                    "nota": result.score,
                    "detalhes": json.dumps(result.details, ensure_ascii=False),
                    "dimensoes": json.dumps(result.dimensions, ensure_ascii=False),
                    "now": now,
                    "ver": RULES_VERSION,
                }
            )
        with engine.begin() as conn:
            if results:
                conn.execute(
                    text(
                        "INSERT INTO analitico.qualidade_conjunto (conjunto_id, nota, detalhes, dimensoes, "
                        "calculada_em, versao_regras) VALUES (:id, :nota, CAST(:detalhes AS jsonb), "
                        "CAST(:dimensoes AS jsonb), :now, :ver) "
                        "ON CONFLICT (conjunto_id) DO UPDATE SET nota = EXCLUDED.nota, detalhes = EXCLUDED.detalhes, "
                        "dimensoes = EXCLUDED.dimensoes, calculada_em = EXCLUDED.calculada_em, "
                        "versao_regras = EXCLUDED.versao_regras"
                    ),
                    results,
                )
                changed = [x for x in results if previous.get(x["id"]) != x["nota"]]
                if changed:
                    conn.execute(
                        text(
                            "INSERT INTO analitico.qualidade_historico (conjunto_id, nota, calculada_em) "
                            "VALUES (:id, :nota, :now)"
                        ),
                        [{"id": x["id"], "nota": x["nota"], "now": now} for x in changed],
                    )
            scored_ids = [x["id"] for x in results]
            # conjuntos que não são pontuáveis (removidos, sem detalhe) ficam sem nota
            conn.execute(
                text(
                    "DELETE FROM analitico.qualidade_conjunto WHERE conjunto_id = ANY(:c) AND NOT (conjunto_id = ANY(:s))"
                ),
                {"c": chunk, "s": scored_ids},
            )
            conn.execute(
                text(
                    "UPDATE analitico.conjunto_busca b SET nota_qualidade = q.nota, "
                    "prioridade = round(((100 - q.nota) * (1 + ln(1 + b.downloads_total)))::numeric, 2) "
                    "FROM analitico.qualidade_conjunto q "
                    "WHERE q.conjunto_id = b.id AND b.id = ANY(:c)"
                ),
                {"c": chunk},
            )
            conn.execute(
                text(
                    "UPDATE analitico.conjunto_busca SET nota_qualidade = NULL, prioridade = NULL "
                    "WHERE id = ANY(:c) AND NOT (id = ANY(:s))"
                ),
                {"c": chunk, "s": scored_ids},
            )
        scored += len(results)
    return scored
