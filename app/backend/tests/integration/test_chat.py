import json
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine

from inspire.api.app import create_app
from inspire.api.deps import get_db
from inspire.config import Settings, get_settings
from inspire.llm import interpret, providers
from inspire.llm.providers import LlmError, LlmRequest, LlmResponse, ProviderInfo

pytestmark = pytest.mark.integration
SIM = Settings(llm_enabled=True, llm_provider="simulado")


class Canned:
    """Provedor que devolve um texto fixo (e guarda o que recebeu)."""

    info = ProviderInfo(nome="falso", modelo="m", externo=True, simulado=False, host="falso.x")

    def __init__(self, text: str) -> None:
        self.text, self.seen = text, []  # type: ignore[var-annotated]

    def complete(self, request: LlmRequest) -> LlmResponse:
        self.seen.append(request)
        return LlmResponse(text=self.text, model="m")


@pytest.fixture
def chat(populated: Engine) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    app.dependency_overrides[get_settings] = lambda: SIM
    yield TestClient(app)


def test_simulado_entende_tema_e_palavras_e_a_busca_executa(chat: TestClient) -> None:
    r = chat.post("/v1/chat/perguntar", json={"pergunta": "dados de saúde da população"})

    assert r.status_code == 200
    body = r.json()
    assert body["filtros_pedidos"].get("tema") == "saude" and body["provedor"]["simulado"] is True
    assert body["resultado"]["total"] >= 0 and "facetas" not in body["resultado"]
    assert "sem IA" in body["explicacao"]


def test_valida_a_saida_do_modelo_e_informa_o_que_descartou(populated: Engine) -> None:
    raw = {
        "q": "vacinas, benefícios;  sociais",
        "tema": "saude, educacao, tema-inventado",
        "formato": ".csv",
        "esfera": "Federal",
        "uf": "xx",
        "organizacao": "Órgão orgao-2",
        "nota_min": 250,
        "explicacao": "ok",
    }
    vocab = interpret.vocabulary(populated)

    result = interpret.validate(populated, raw, vocab)

    assert result.filtros["esfera"] == "federal" and result.filtros["nota_min"] == 100.0
    assert (
        result.filtros["organizacao"] == "orgao-2"
        and result.filtros["q"] == "vacinas benefícios sociais"
    )
    assert result.filtros["tema"] == "saude,educacao" and "uf" not in result.filtros
    assert any("tema-inventado" in i for i in result.ignorados) and any(
        "uf" in i for i in result.ignorados
    )


def test_so_o_texto_e_o_vocabulario_vao_ao_provedor(populated: Engine) -> None:
    fake = Canned('```json\n{"q": "população", "tema": "saude"}\n```')

    result = interpret.interpret(populated, fake, "  dados   de saúde  ")

    sent = fake.seen[0]
    assert (
        "dados de saúde" in sent.user and "saude" in sent.user
    )  # espaços normalizados, vocabulário incluso
    assert set(sent.context) == {
        "pergunta",
        "temas",
        "formatos",
    }  # nada do catálogo curado nem contatos
    assert result.filtros == {"q": "população", "tema": "saude"}


def test_resposta_ruim_do_modelo_vira_erro_claro(populated: Engine) -> None:
    with pytest.raises(LlmError, match="entender"):
        interpret.interpret(populated, Canned("não sei"), "qualquer coisa")
    with pytest.raises(LlmError, match="entender"):
        interpret.interpret(populated, Canned('{"q": '), "qualquer coisa")
    with pytest.raises(ValueError, match="pergunta"):
        interpret.interpret(populated, Canned("{}"), "   ")


def test_rota_com_recurso_desligado_e_com_falha_do_provedor(
    populated: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    client = TestClient(app)  # LLM desligado por padrão
    r = client.post("/v1/chat/perguntar", json={"pergunta": "saúde"})
    assert r.status_code == 409 and "desligado" in r.json()["detail"]

    app.dependency_overrides[get_settings] = lambda: SIM
    monkeypatch.setattr(providers, "build_provider", lambda _s: Canned("{"))
    r = client.post("/v1/chat/perguntar", json={"pergunta": "saúde"})
    assert r.status_code == 502 and "entender" in r.json()["detail"]
    assert client.post("/v1/chat/perguntar", json={"pergunta": "x"}).status_code == 422


def test_modelo_com_filtros_validos_filtra_de_verdade(
    populated: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    app.dependency_overrides[get_settings] = lambda: SIM
    monkeypatch.setattr(
        providers, "build_provider", lambda _s: Canned(json.dumps({"organizacao": "orgao-1"}))
    )

    r = TestClient(app).post("/v1/chat/perguntar", json={"pergunta": "tudo do órgão 1"}).json()

    assert r["provedor"]["externo"] is True and r["organizacao"]["slug"] == "orgao-1"
    assert r["resultado"]["total"] > 0
    assert {i["organizacao_slug"] for i in r["resultado"]["itens"]} == {"orgao-1"}


def test_sem_resultado_solta_filtros_especulativos_e_informa(
    populated: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    app.dependency_overrides[get_settings] = lambda: SIM
    answer = {"organizacao": "orgao-1", "esfera": "municipal", "periodicidade": "DIARIA"}
    monkeypatch.setattr(providers, "build_provider", lambda _s: Canned(json.dumps(answer)))

    r = TestClient(app).post("/v1/chat/perguntar", json={"pergunta": "do órgão 1"}).json()

    assert r["filtros_pedidos"].keys() == {"organizacao", "esfera", "periodicidade"}
    assert r["filtros_removidos"] == ["periodicidade", "esfera"]  # nessa ordem; o órgão fica
    assert r["filtros"] == {"organizacao": "orgao-1"} and r["resultado"]["total"] > 0


def test_propor_colecao_nao_cria_nada_e_nao_afrouxa(
    populated: Engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    app.dependency_overrides[get_settings] = lambda: SIM
    answer = {"organizacao": "orgao-1", "esfera": "municipal"}
    monkeypatch.setattr(providers, "build_provider", lambda _s: Canned(json.dumps(answer)))
    client = TestClient(app)
    before = len(client.get("/v1/colecoes").json())

    r = client.post("/v1/chat/colecao", json={"descricao": "bases do órgão 1 municipais, só isso"})

    body = r.json()
    assert r.status_code == 200 and body["filtros"] == {
        "organizacao": "orgao-1",
        "esfera": "municipal",
    }
    assert body["resultado"]["total"] == 0  # sem afrouxar: reflete exatamente o pedido
    assert body["nome_sugerido"].startswith("Bases do órgão 1")
    assert len(client.get("/v1/colecoes").json()) == before  # nada foi criado
    assert client.post("/v1/chat/colecao", json={"descricao": "x"}).status_code == 422
