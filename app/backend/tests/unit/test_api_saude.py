from fastapi.testclient import TestClient

from inspire import __version__
from inspire.api.app import create_app
from inspire.api.routes.saude import get_db_check


def _client(db_up: bool) -> TestClient:
    app = create_app()
    app.dependency_overrides[get_db_check] = lambda: lambda: db_up
    return TestClient(app)


def test_saude_ok_quando_banco_responde() -> None:
    response = _client(db_up=True).get("/v1/saude")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "banco": "ok", "versao": __version__}


def test_saude_degradado_quando_banco_cai() -> None:
    response = _client(db_up=False).get("/v1/saude")

    assert response.status_code == 503
    assert response.json()["status"] == "degradado"
    assert response.json()["banco"] == "indisponivel"


def test_openapi_documenta_a_api_versionada() -> None:
    spec = _client(db_up=True).get("/openapi.json").json()

    assert spec["info"]["title"] == "Inspire Catálogo"
    assert "/v1/saude" in spec["paths"]
