"""Normalizador: JSON bruto do portal -> tabelas do schema `catalogo`.

É idempotente: reprocessar o mesmo documento produz o mesmo catálogo (ADR-0005). Recebe sempre uma
``Connection`` já aberta, para o chamador decidir a transação.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import Connection, text

TZ = ZoneInfo("America/Sao_Paulo")
ESFERAS = {"1": "federal", "2": "estadual", "3": "municipal"}
_DATE_FORMATS = ("%d/%m/%Y %H:%M:%S", "%d/%m/%Y", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d")


def parse_portal_datetime(value: Any) -> datetime | None:
    """Datas do portal vêm como texto `dd/mm/aaaa [hh:mm:ss]`; valores inválidos viram None."""
    if not isinstance(value, str) or not value.strip():
        return None
    for fmt in _DATE_FORMATS:
        try:
            return datetime.strptime(value.strip(), fmt).replace(tzinfo=TZ)
        except ValueError:
            continue
    return None


def _yes_no(value: Any) -> bool | None:
    if value is None:
        return None
    return str(value).strip().lower() in {"sim", "true", "1", "s"}


def _int(value: Any) -> int | None:
    try:
        return None if value is None else int(value)
    except (TypeError, ValueError):
        return None


def resource_id(conjunto_id: str, resource: dict[str, Any]) -> str:
    """Recursos têm `id`; na falta dele, deriva um estável a partir do conjunto e do link."""
    if resource.get("id"):
        return str(resource["id"])
    base = f"{conjunto_id}|{resource.get('link')}|{resource.get('numOrdem')}"
    return "derivado-" + hashlib.sha1(base.encode(), usedforsecurity=False).hexdigest()[:20]


# ------------------------------------------------------------------ dimensões


def upsert_organization(conn: Connection, doc: dict[str, Any]) -> None:
    conn.execute(
        text(
            "INSERT INTO catalogo.organizacao (slug, id, titulo, descricao, esfera, uf, municipio, "
            "qtd_declarada, atualizado_em) VALUES (:slug, :id, :titulo, :descricao, :esfera, :uf, "
            ":municipio, :qtd, now()) ON CONFLICT (slug) DO UPDATE SET id = EXCLUDED.id, "
            "titulo = EXCLUDED.titulo, descricao = EXCLUDED.descricao, esfera = EXCLUDED.esfera, "
            "uf = EXCLUDED.uf, municipio = EXCLUDED.municipio, qtd_declarada = EXCLUDED.qtd_declarada, "
            "atualizado_em = now()"
        ),
        {
            "slug": doc["nome"],
            "id": doc.get("id"),
            "titulo": doc.get("titulo") or doc["nome"],
            "descricao": doc.get("descricao"),
            "esfera": ESFERAS.get(str(doc.get("organizationEsfera") or "")),
            "uf": doc.get("organizationUf") or None,
            "municipio": doc.get("organizationMunicipio") or None,
            "qtd": _int(doc.get("qtdConjuntoDeDados")) or 0,
        },
    )


def upsert_themes(conn: Connection, themes: list[dict[str, Any]]) -> None:
    for t in themes:
        conn.execute(
            text(
                "INSERT INTO catalogo.tema (slug, id, titulo, descricao) VALUES (:slug, :id, :titulo, :d) "
                "ON CONFLICT (slug) DO UPDATE SET id = EXCLUDED.id, titulo = EXCLUDED.titulo, "
                "descricao = EXCLUDED.descricao"
            ),
            {
                "slug": t["name"],
                "id": t.get("id"),
                "titulo": t.get("title") or t["name"],
                "d": t.get("description"),
            },
        )


def upsert_formats(conn: Connection, formats: list[str]) -> None:
    rows = [{"n": f} for f in formats if isinstance(f, str) and f.strip()]
    if rows:
        conn.execute(
            text("INSERT INTO catalogo.formato (nome) VALUES (:n) ON CONFLICT DO NOTHING"), rows
        )


def upsert_legal_basis(conn: Connection, items: list[dict[str, Any]]) -> None:
    rows = [{"id": i["id"], "d": i["descricao"]} for i in items if "id" in i and i.get("descricao")]
    if rows:
        conn.execute(
            text(
                "INSERT INTO catalogo.observancia_legal (id, descricao) VALUES (:id, :d) "
                "ON CONFLICT (id) DO UPDATE SET descricao = EXCLUDED.descricao"
            ),
            rows,
        )


# ------------------------------------------------------------------ conjuntos


def normalize_conjunto(
    conn: Connection,
    run_id: int,
    detail: dict[str, Any],
    *,
    doc_hash: str,
    listing_change: str | None,
) -> str | None:
    """Grava o conjunto e seus filhos. Devolve o evento ('novo', 'alterado', 'reaparecido') ou None."""
    cid = str(detail["id"])
    prev = conn.execute(
        text("SELECT hash_atual, removido_em, sem_detalhe FROM catalogo.conjunto WHERE id = :id"),
        {"id": cid},
    ).first()
    if prev is None:
        event: str | None = "novo"
    elif prev.removido_em is not None:
        event = "reaparecido"
    elif prev.hash_atual != doc_hash or prev.sem_detalhe:
        event = "alterado"
    else:
        event = None

    recursos = [r for r in (detail.get("recursos") or []) if isinstance(r, dict)]
    conn.execute(
        text(
            """
            INSERT INTO catalogo.conjunto (
                id, slug, titulo, descricao, organizacao_slug, licenca, periodicidade,
                cobertura_temporal_inicio, cobertura_temporal_fim, cobertura_espacial,
                granularidade_espacial, versao, descontinuado, dados_abertos, selo_portal,
                atualizado_portal, origem_cadastro, visibilidade, observancia_legal,
                tem_responsavel, tem_email_responsavel, catalogado_em, metadados_atualizados_em,
                dados_atualizados_em, alteracao_listagem, qtd_recursos, sem_detalhe, hash_atual,
                ultima_vez_em, removido_em)
            VALUES (
                :id, :slug, :titulo, :descricao, :org, :licenca, :periodicidade,
                :cti, :ctf, :ce, :ge, :versao, :descontinuado, :dados_abertos, :selo,
                :atualizado, :origem, :visibilidade, :observancia, :tem_resp, :tem_email,
                :catalogado, :meta, :dados, :alteracao_listagem, :qtd_recursos, false, :hash,
                now(), NULL)
            ON CONFLICT (id) DO UPDATE SET
                slug = EXCLUDED.slug, titulo = EXCLUDED.titulo, descricao = EXCLUDED.descricao,
                organizacao_slug = EXCLUDED.organizacao_slug, licenca = EXCLUDED.licenca,
                periodicidade = EXCLUDED.periodicidade,
                cobertura_temporal_inicio = EXCLUDED.cobertura_temporal_inicio,
                cobertura_temporal_fim = EXCLUDED.cobertura_temporal_fim,
                cobertura_espacial = EXCLUDED.cobertura_espacial,
                granularidade_espacial = EXCLUDED.granularidade_espacial, versao = EXCLUDED.versao,
                descontinuado = EXCLUDED.descontinuado, dados_abertos = EXCLUDED.dados_abertos,
                selo_portal = EXCLUDED.selo_portal, atualizado_portal = EXCLUDED.atualizado_portal,
                origem_cadastro = EXCLUDED.origem_cadastro, visibilidade = EXCLUDED.visibilidade,
                observancia_legal = EXCLUDED.observancia_legal,
                tem_responsavel = EXCLUDED.tem_responsavel,
                tem_email_responsavel = EXCLUDED.tem_email_responsavel,
                catalogado_em = EXCLUDED.catalogado_em,
                metadados_atualizados_em = EXCLUDED.metadados_atualizados_em,
                dados_atualizados_em = EXCLUDED.dados_atualizados_em,
                alteracao_listagem = EXCLUDED.alteracao_listagem,
                qtd_recursos = EXCLUDED.qtd_recursos, sem_detalhe = false,
                hash_atual = EXCLUDED.hash_atual, ultima_vez_em = now(), removido_em = NULL
            """
        ),
        {
            "id": cid,
            "slug": detail.get("nome"),
            "titulo": detail.get("titulo") or detail.get("nome") or cid,
            "descricao": detail.get("descricao"),
            "org": detail.get("organizacao"),
            "licenca": detail.get("licenca"),
            "periodicidade": detail.get("periodicidade"),
            "cti": detail.get("coberturaTemporalInicio"),
            "ctf": detail.get("coberturaTemporalFim"),
            "ce": detail.get("coberturaEspacial"),
            "ge": detail.get("granularidadeEspacial"),
            "versao": detail.get("versao"),
            "descontinuado": bool(detail.get("descontinuado")),
            "dados_abertos": _yes_no(detail.get("dadosAbertos")),
            "selo": detail.get("selo"),
            "atualizado": detail.get("atualizado"),
            "origem": detail.get("origemCadastro"),
            "visibilidade": detail.get("visibilidade"),
            "observancia": detail.get("observanciaLegal"),
            "tem_resp": bool(detail.get("temResponsavel")),
            "tem_email": bool(detail.get("temEmailResponsavel")),
            "catalogado": parse_portal_datetime(detail.get("dataCatalogacao")),
            "meta": parse_portal_datetime(detail.get("dataUltimaAtualizacaoMetadados")),
            "dados": parse_portal_datetime(detail.get("dataUltimaAtualizacaoArquivo")),
            "alteracao_listagem": listing_change,
            "qtd_recursos": len(recursos),
            "hash": doc_hash,
        },
    )
    if event is None:
        return None

    _replace_children(conn, cid, detail, recursos)
    conn.execute(
        text(
            "INSERT INTO catalogo.conjunto_historico (conjunto_id, execucao_id, evento) "
            "VALUES (:c, :r, :e)"
        ),
        {"c": cid, "r": run_id, "e": event},
    )
    return event


def _replace_children(
    conn: Connection, cid: str, detail: dict[str, Any], recursos: list[dict[str, Any]]
) -> None:
    for table in ("recurso", "conjunto_tema", "conjunto_tag", "conjunto_associado"):
        conn.execute(text(f"DELETE FROM catalogo.{table} WHERE conjunto_id = :c"), {"c": cid})  # noqa: S608

    if recursos:
        conn.execute(
            text(
                "INSERT INTO catalogo.recurso (id, conjunto_id, titulo, descricao, formato, tipo, link, "
                "nome_arquivo, tamanho, downloads, ordem, catalogado_em, atualizado_em) VALUES "
                "(:id, :c, :titulo, :descricao, :formato, :tipo, :link, :arquivo, :tamanho, :downloads, "
                ":ordem, :cat, :atu) ON CONFLICT (id) DO UPDATE SET conjunto_id = EXCLUDED.conjunto_id, "
                "titulo = EXCLUDED.titulo, descricao = EXCLUDED.descricao, formato = EXCLUDED.formato, "
                "tipo = EXCLUDED.tipo, link = EXCLUDED.link, nome_arquivo = EXCLUDED.nome_arquivo, "
                "tamanho = EXCLUDED.tamanho, downloads = EXCLUDED.downloads, ordem = EXCLUDED.ordem, "
                "catalogado_em = EXCLUDED.catalogado_em, atualizado_em = EXCLUDED.atualizado_em"
            ),
            [
                {
                    "id": resource_id(cid, r),
                    "c": cid,
                    "titulo": r.get("titulo"),
                    "descricao": r.get("descricao"),
                    "formato": r.get("formato"),
                    "tipo": r.get("tipo"),
                    "link": r.get("link"),
                    "arquivo": r.get("nomeArquivo"),
                    "tamanho": _int(r.get("tamanho")),
                    "downloads": _int(r.get("quantidadeDownloads")),
                    "ordem": _int(r.get("numOrdem")),
                    "cat": parse_portal_datetime(r.get("dataCatalogacao")),
                    "atu": parse_portal_datetime(r.get("dataUltimaAtualizacaoArquivo")),
                }
                for r in recursos
            ],
        )

    themes = [t for t in (detail.get("temas") or []) if isinstance(t, dict) and t.get("name")]
    if themes:
        conn.execute(
            text("INSERT INTO catalogo.tema (slug, titulo) VALUES (:s, :t) ON CONFLICT DO NOTHING"),
            [{"s": t["name"], "t": t.get("title") or t["name"]} for t in themes],
        )
        conn.execute(
            text(
                "INSERT INTO catalogo.conjunto_tema (conjunto_id, tema_slug) VALUES (:c, :s) ON CONFLICT DO NOTHING"
            ),
            [{"c": cid, "s": t["name"]} for t in themes],
        )

    tags = sorted(
        {t["name"] for t in (detail.get("tags") or []) if isinstance(t, dict) and t.get("name")}
    )
    if tags:
        conn.execute(
            text("INSERT INTO catalogo.tag (nome) VALUES (:n) ON CONFLICT DO NOTHING"),
            [{"n": n} for n in tags],
        )
        conn.execute(
            text(
                "INSERT INTO catalogo.conjunto_tag (conjunto_id, tag_nome) VALUES (:c, :n) ON CONFLICT DO NOTHING"
            ),
            [{"c": cid, "n": n} for n in tags],
        )

    assoc = {
        str(a["id"]) if isinstance(a, dict) and a.get("id") else str(a)
        for a in (detail.get("conjuntoDadosAssociados") or [])
        if a
    }
    if assoc:
        conn.execute(
            text(
                "INSERT INTO catalogo.conjunto_associado (conjunto_id, associado_id) VALUES (:c, :a) ON CONFLICT DO NOTHING"
            ),
            [{"c": cid, "a": a} for a in sorted(assoc)],
        )


def normalize_without_detail(conn: Connection, run_id: int, summary: dict[str, Any]) -> str | None:
    """Conjunto listado cujo detalhe o portal não entrega: guarda o resumo e marca `sem_detalhe`."""
    cid = str(summary["id"])
    existed = conn.execute(
        text("SELECT 1 FROM catalogo.conjunto WHERE id = :id"), {"id": cid}
    ).first()
    conn.execute(
        text(
            "INSERT INTO catalogo.conjunto (id, slug, titulo, organizacao_slug, catalogado_em, "
            "metadados_atualizados_em, alteracao_listagem, sem_detalhe, ultima_vez_em) "
            "VALUES (:id, :slug, :titulo, :org, :cat, :meta, :alt, true, now()) "
            "ON CONFLICT (id) DO UPDATE SET sem_detalhe = true, alteracao_listagem = EXCLUDED.alteracao_listagem, "
            "ultima_vez_em = now(), removido_em = NULL"
        ),
        {
            "id": cid,
            "slug": summary.get("nome"),
            "titulo": summary.get("title") or summary.get("nome") or cid,
            "org": summary.get("nomeOrganizacao"),
            "cat": parse_portal_datetime(summary.get("catalogacao")),
            "meta": parse_portal_datetime(summary.get("ultimaAlteracaoMetadados")),
            "alt": summary.get("ultimaAlteracaoMetadados"),
        },
    )
    if existed:
        return None
    conn.execute(
        text(
            "INSERT INTO catalogo.conjunto_historico (conjunto_id, execucao_id, evento) VALUES (:c, :r, 'novo')"
        ),
        {"c": cid, "r": run_id},
    )
    return "novo"


def mark_removed(conn: Connection, run_id: int) -> int:
    """Marca como removidos os conjuntos que a listagem desta execução não trouxe."""
    rows = conn.execute(
        text(
            "UPDATE catalogo.conjunto c SET removido_em = :agora WHERE c.removido_em IS NULL AND NOT EXISTS "
            "(SELECT 1 FROM raw.fila_detalhe f WHERE f.execucao_id = :r AND f.conjunto_id = c.id) RETURNING c.id"
        ),
        {"agora": datetime.now(UTC), "r": run_id},
    ).all()
    if rows:
        conn.execute(
            text(
                "INSERT INTO catalogo.conjunto_historico (conjunto_id, execucao_id, evento) VALUES (:c, :r, 'removido')"
            ),
            [{"c": r.id, "r": run_id} for r in rows],
        )
    return len(rows)
