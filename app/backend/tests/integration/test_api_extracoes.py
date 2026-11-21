from collections.abc import Iterator
from datetime import timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from inspire.api.app import create_app
from inspire.api.deps import get_db, get_policy
from inspire.extraction.control import Policy
from support.helpers import scalar

pytestmark = pytest.mark.integration


@pytest.fixture
def client(db: Engine) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: db
    app.dependency_overrides[get_policy] = lambda: Policy()
    yield TestClient(app)


def finish(db: Engine, run_id: int, state: str = "concluida") -> None:
    with db.begin() as conn:
        conn.execute(
            text(
                "UPDATE raw.execucao SET estado = :s, iniciada_em = now(), finalizada_em = now() WHERE id = :r"
            ),
            {"s": state, "r": run_id},
        )


def test_primeiro_pedido_devolve_202_e_a_execucao(client: TestClient) -> None:
    r = client.post("/v1/extracoes", json={"tipo": "incremental"})

    assert r.status_code == 202
    body = r.json()
    assert (
        body["estado"] == "enfileirada"
        and body["tipo"] == "incremental"
        and body["forcada"] is False
    )


def test_cliques_repetidos_devolvem_a_mesma_execucao_sem_criar_outra(
    client: TestClient, db: Engine
) -> None:
    first = client.post("/v1/extracoes", json={}).json()

    responses = [client.post("/v1/extracoes", json={}) for _ in range(10)]

    assert all(r.status_code == 200 for r in responses)
    assert {r.json()["id"] for r in responses} == {first["id"]}
    assert scalar(db, "SELECT count(*) FROM raw.execucao") == 1


def test_dentro_do_intervalo_devolve_429_com_motivo_e_horario(
    client: TestClient, db: Engine
) -> None:
    run = client.post("/v1/extracoes", json={}).json()["id"]
    finish(db, run)

    r = client.post("/v1/extracoes", json={})

    assert r.status_code == 429
    assert "Intervalo" in r.json()["motivo"]
    assert r.json()["disponivel_em"]


def test_forcar_ignora_o_intervalo(client: TestClient, db: Engine) -> None:
    run = client.post("/v1/extracoes", json={}).json()["id"]
    finish(db, run)

    r = client.post("/v1/extracoes", json={"forcar": True})

    assert r.status_code == 202 and r.json()["forcada"] is True


def test_estado_orienta_o_botao_da_tela(client: TestClient, db: Engine) -> None:
    vazio = client.get("/v1/extracoes/estado").json()
    assert vazio["incremental"]["pode_pedir"] is True and vazio["ativa"] is None
    assert vazio["sugerir_completa"] is True and vazio["ultima_completa_em"] is None

    run = client.post("/v1/extracoes", json={"tipo": "completa"}).json()["id"]
    durante = client.get("/v1/extracoes/estado").json()
    assert durante["ativa"]["id"] == run and durante["incremental"]["pode_pedir"] is False

    finish(db, run)
    depois = client.get("/v1/extracoes/estado").json()
    assert depois["completa"]["pode_pedir"] is False and depois["completa"]["disponivel_em"]
    assert depois["dias_desde_ultima_completa"] == 0 and depois["sugerir_completa"] is False


def test_listar_detalhar_e_cancelar(client: TestClient) -> None:
    run = client.post("/v1/extracoes", json={}).json()["id"]

    assert [e["id"] for e in client.get("/v1/extracoes").json()] == [run]
    assert client.get(f"/v1/extracoes/{run}").json()["id"] == run
    assert client.get("/v1/extracoes/999").status_code == 404

    assert client.post(f"/v1/extracoes/{run}/cancelar").json() == {"resultado": "cancelada"}
    assert client.post(f"/v1/extracoes/{run}/cancelar").status_code == 409


def test_tipo_invalido_e_recusado(client: TestClient) -> None:
    assert client.post("/v1/extracoes", json={"tipo": "qualquer"}).status_code == 422


def test_politica_vem_da_configuracao(client: TestClient, db: Engine) -> None:
    client.app.dependency_overrides[get_policy] = lambda: Policy(min_incremental=timedelta(0))  # type: ignore[attr-defined]
    run = client.post("/v1/extracoes", json={}).json()["id"]
    finish(db, run)

    assert client.post("/v1/extracoes", json={}).status_code == 202
