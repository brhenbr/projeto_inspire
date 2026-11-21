"""Servidor HTTP do portal falso, para os testes E2E (uvicorn --app-dir tests support.fake_portal_app:app).

Também expõe /_teste/* para os testes alterarem o "portal" durante o cenário.
"""

import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, Response

from support.fake_portal import FakePortal

portal = FakePortal(
    n_datasets=int(os.environ.get("FAKE_PORTAL_DATASETS", "40")),
    n_orgs=int(os.environ.get("FAKE_PORTAL_ORGS", "3")),
    flaky_every=int(os.environ.get("FAKE_PORTAL_FLAKY_EVERY", "7")),
    bad_ids={"ds-0003"},
)
portal.add("ds-saude", "orgao-1", 1)
portal.update_title("ds-saude", "Saúde da População Brasileira")
portal.datasets["ds-saude"]["descricao"] = (
    "Indicadores de mortalidade e internações hospitalares por município. " * 3
)
app = FastAPI(title="Portal falso")


@app.post("/_teste/titulo/{dataset_id}")
def mudar_titulo(dataset_id: str, titulo: str) -> dict[str, str]:
    portal.update_title(dataset_id, titulo)
    return {"ok": "sim"}


@app.post("/_teste/remover/{dataset_id}")
def remover(dataset_id: str) -> dict[str, str]:
    portal.remove(dataset_id)
    return {"ok": "sim"}


@app.get("/_teste/chamadas")
def chamadas() -> dict[str, int]:
    return dict(portal.calls)


@app.get("/{path:path}")
def qualquer(path: str, request: Request) -> Response:
    status, body = portal.handle(
        "/" + path, dict(request.query_params), request.headers.get("chave-api-dados-abertos")
    )
    if body is None:
        return Response(status_code=status)
    return JSONResponse(body, status_code=status)
