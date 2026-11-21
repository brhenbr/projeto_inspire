"""Montagem de cliente e execuções para os testes."""

import httpx
from sqlalchemy import Engine, text

from inspire.extraction.portal_client import PortalClient
from inspire.extraction.raw_store import RawStore
from inspire.extraction.runner import ExtractionRunner
from support.fake_portal import API_KEY, FakePortal


def make_client(portal: FakePortal, key: str = API_KEY) -> PortalClient:
    def handler(request: httpx.Request) -> httpx.Response:
        status, body = portal.handle(
            request.url.path,
            dict(request.url.params),
            request.headers.get("chave-api-dados-abertos"),
        )
        return httpx.Response(status, json=body) if body is not None else httpx.Response(status)

    return PortalClient(
        "https://portal.test",
        key,
        transport=httpx.MockTransport(handler),
        sleep=lambda _s: None,
        rng=lambda: 0.0,
        max_retries=6,
        empty_retries=4,
    )


def run_extraction(engine: Engine, portal: FakePortal, kind: str = "completa") -> tuple[int, str]:
    run_id = RawStore(engine).create_run(kind)
    with make_client(portal) as client:
        state = ExtractionRunner(engine, client, concurrency=2).run(run_id)
    return run_id, state


def scalar(engine: Engine, sql: str, **params: object) -> object:
    with engine.connect() as conn:
        return conn.execute(text(sql), params).scalar_one()


def rows(engine: Engine, sql: str, **params: object) -> list[object]:
    with engine.connect() as conn:
        return list(conn.execute(text(sql), params).all())


def reset_database(engine: Engine) -> None:
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL lock_timeout = '10s'"))  # falha rápido, nunca trava
        conn.execute(
            text(
                "TRUNCATE raw.fila_detalhe, raw.visto, raw.documento, raw.execucao, "
                "catalogo.conjunto_historico, catalogo.conjunto_associado, catalogo.conjunto_tag, "
                "catalogo.conjunto_tema, catalogo.recurso, catalogo.conjunto, catalogo.tag, "
                "catalogo.observancia_legal, catalogo.formato, catalogo.tema, catalogo.organizacao "
                "RESTART IDENTITY CASCADE"
            )
        )
