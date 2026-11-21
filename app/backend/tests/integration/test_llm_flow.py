import json
from collections.abc import Iterator

import httpx
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, text

from inspire.api.app import create_app
from inspire.api.deps import get_db
from inspire.config import Settings, get_settings
from inspire.curation import service as curation
from inspire.llm import providers, service
from inspire.llm.providers import OpenAICompatibleProvider
from inspire.llm.service import ConflictError
from support.fake_portal import FakePortal
from support.helpers import run_extraction, scalar

pytestmark = pytest.mark.integration

SIM = Settings(llm_enabled=True, llm_provider="simulado", llm_request_interval_s=0)


def make_execution(db: Engine, task: str, ids: list[str], instructions: str | None = None) -> int:
    return service.create_execution(
        db, SIM, task, ids, instructions=instructions, requested_by="ana"
    )


def run_all(db: Engine) -> None:
    while service.process_next(db, SIM):
        pass


def proposals(db: Engine, **where: object) -> list[dict]:  # type: ignore[type-arg]
    clause = " AND ".join(f"{k} = :{k}" for k in where) or "true"
    with db.connect() as conn:
        rows = conn.execute(
            text(f"SELECT * FROM curadoria.llm_proposta WHERE {clause} ORDER BY id"), where
        ).all()
    return [dict(r._mapping) for r in rows]


# ----------------------------------------------------------------- execução


def test_execucao_gera_propostas_e_nao_altera_o_catalogo(populated: Engine) -> None:
    antes = scalar(
        populated,
        "SELECT titulo || coalesce(descricao,'') FROM analitico.conjunto_busca WHERE id = 'ds-0001'",
    )
    ex = make_execution(populated, "melhorar-descricao", ["ds-0001", "ds-0002"])

    run_all(populated)

    assert (
        scalar(populated, "SELECT estado FROM curadoria.llm_execucao WHERE id = :i", i=ex)
        == "concluida"
    )
    props = proposals(populated, execucao_id=ex)
    assert len(props) == 2 and {p["estado"] for p in props} == {"pendente"}
    assert all(p["valor_proposto"] and p["prompt"] and p["resposta_bruta"] for p in props)
    assert (
        scalar(
            populated,
            "SELECT titulo || coalesce(descricao,'') FROM analitico.conjunto_busca WHERE id = 'ds-0001'",
        )
        == antes
    )
    assert (
        scalar(populated, "SELECT count(*) FROM curadoria.alteracao") == 0
    )  # nada aplicado sem aprovação


def test_proveniencia_fica_registrada_na_execucao(populated: Engine) -> None:
    ex = make_execution(populated, "sugerir-tags", ["ds-0001"], "foco em orçamento")

    with populated.connect() as conn:
        row = conn.execute(
            text(
                "SELECT provedor, modelo, externo, tarefa_versao, solicitada_por, parametros FROM curadoria.llm_execucao WHERE id = :i"
            ),
            {"i": ex},
        ).one()
    assert tuple(row)[:5] == ("simulado", "regras-simples-v1", False, 1, "ana")
    assert row.parametros["instrucoes"] == "foco em orçamento"


def test_prompt_enviado_ao_provedor_tem_so_campos_publicos(
    populated: Engine, portal: FakePortal
) -> None:
    sent: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        sent.append(request.content.decode())
        return httpx.Response(
            200, json={"model": "m", "choices": [{"message": {"content": '{"tags": ["teste"]}'}}]}
        )

    provider = OpenAICompatibleProvider(
        "https://llm.exemplo.org/v1", "k", "m", transport=httpx.MockTransport(handler)
    )
    ex = make_execution(populated, "sugerir-tags", ["ds-0001", "ds-0002"])
    service.claim_next(populated)

    service.run_execution(populated, provider, ex)

    assert len(sent) == 2
    corpo = " ".join(sent)
    assert (
        "@orgao-" not in corpo and "Responsável " not in corpo and "emailResponsavel" not in corpo
    )
    assert "Conjunto ds-0001" in sent[0]  # mas o título (público) vai


def test_um_conjunto_por_chamada(populated: Engine) -> None:
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        return httpx.Response(
            200, json={"model": "m", "choices": [{"message": {"content": '{"tags": ["a"]}'}}]}
        )

    provider = OpenAICompatibleProvider(
        "https://llm.exemplo.org/v1", "k", "m", transport=httpx.MockTransport(handler)
    )
    ex = make_execution(populated, "sugerir-tags", ["ds-0001", "ds-0002", "ds-0003"])
    service.claim_next(populated)

    service.run_execution(populated, provider, ex)

    assert len(calls) == 3


def test_resposta_invalida_do_modelo_vira_proposta_com_erro_sem_derrubar_o_lote(
    populated: Engine,
) -> None:
    answers = iter(["texto sem json", '{"tags": ["boa"]}'])

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200, json={"model": "m", "choices": [{"message": {"content": next(answers)}}]}
        )

    provider = OpenAICompatibleProvider(
        "https://llm.exemplo.org/v1", "k", "m", transport=httpx.MockTransport(handler)
    )
    ex = make_execution(populated, "sugerir-tags", ["ds-0001", "ds-0002"])
    service.claim_next(populated)

    assert service.run_execution(populated, provider, ex) == "concluida"

    estados = [p["estado"] for p in proposals(populated, execucao_id=ex)]
    assert sorted(estados) == ["erro", "pendente"]
    assert (
        scalar(populated, "SELECT totais->>'erros' FROM curadoria.llm_execucao WHERE id = :i", i=ex)
        == "1"
    )


def test_falha_do_provedor_vira_erro_do_item(populated: Engine) -> None:
    provider = OpenAICompatibleProvider(
        "https://llm.exemplo.org/v1",
        "k",
        "m",
        transport=httpx.MockTransport(lambda r: httpx.Response(401)),
        sleep=lambda _s: None,
    )
    ex = make_execution(populated, "sugerir-tags", ["ds-0001"])
    service.claim_next(populated)

    service.run_execution(populated, provider, ex)

    p = proposals(populated, execucao_id=ex)[0]
    assert p["estado"] == "erro" and "credencial" in p["erro"]


def test_sem_mudanca_nao_gera_proposta(populated: Engine) -> None:
    class Eco:
        info = providers.SimulatedProvider.info

        def complete(self, request):  # type: ignore[no-untyped-def]
            return providers.LlmResponse(
                text=json.dumps({"tags": request.context["tags"] or ["x"]}), model="eco"
            )

    with populated.begin() as conn:
        conn.execute(text("INSERT INTO catalogo.tag (nome) VALUES ('x') ON CONFLICT DO NOTHING"))
    curation.apply_changes(populated, "ds-0001", {"tags": ["x"]}, author="ana")
    ex = make_execution(populated, "sugerir-tags", ["ds-0001"])
    service.claim_next(populated)

    service.run_execution(populated, Eco(), ex)  # type: ignore[arg-type]

    assert proposals(populated, execucao_id=ex) == []
    assert (
        scalar(
            populated,
            "SELECT totais->>'sem_mudanca' FROM curadoria.llm_execucao WHERE id = :i",
            i=ex,
        )
        == "1"
    )


def test_conjunto_inexistente_ou_sem_detalhe_vira_erro_do_item(populated: Engine) -> None:
    ex = make_execution(populated, "sugerir-tags", ["nao-existe"])
    run_all(populated)

    p = proposals(populated, execucao_id=ex)[0]
    assert p["estado"] == "erro" and "indisponível" in p["erro"]


def test_so_uma_execucao_por_vez_e_limites(populated: Engine) -> None:
    make_execution(populated, "sugerir-tags", ["ds-0001"])

    with pytest.raises(ConflictError):
        make_execution(populated, "sugerir-tags", ["ds-0002"])
    run_all(populated)
    with pytest.raises(curation.CurationError):
        make_execution(populated, "sugerir-tags", [])
    with pytest.raises(curation.CurationError):
        make_execution(populated, "inexistente", ["ds-0001"])
    with pytest.raises(curation.CurationError, match="no máximo"):
        make_execution(populated, "sugerir-tags", [f"id-{i}" for i in range(201)])


def test_desligado_nao_cria_execucao(populated: Engine) -> None:
    with pytest.raises(providers.LlmDisabledError):
        service.create_execution(
            populated,
            Settings(),
            "sugerir-tags",
            ["ds-0001"],
            instructions=None,
            requested_by="ana",
        )


def test_cancelar_execucao_enfileirada_e_em_andamento(populated: Engine) -> None:
    ex = make_execution(populated, "sugerir-tags", ["ds-0001", "ds-0002"])
    assert service.cancel_execution(populated, ex) == "cancelada"
    assert service.cancel_execution(populated, ex) is None

    ex2 = make_execution(populated, "sugerir-tags", ["ds-0001", "ds-0002"])
    service.claim_next(populated)
    assert service.cancel_execution(populated, ex2) == "cancelamento_solicitado"
    assert service.run_execution(populated, providers.SimulatedProvider(), ex2) == "cancelada"
    assert proposals(populated, execucao_id=ex2) == []


def test_execucao_interrompida_volta_para_a_fila(populated: Engine) -> None:
    ex = make_execution(populated, "sugerir-tags", ["ds-0001"])
    service.claim_next(populated)

    assert service.requeue_interrupted(populated) == 1
    assert service.claim_next(populated) == ex


# ----------------------------------------------------------------- decisão humana


def first_proposal(db: Engine, task: str = "melhorar-descricao", ds: str = "ds-0001") -> dict:  # type: ignore[type-arg]
    ex = make_execution(db, task, [ds])
    run_all(db)
    return proposals(db, execucao_id=ex)[0]


def test_aprovar_aplica_a_curadoria_com_origem_llm_e_rastro(populated: Engine) -> None:
    p = first_proposal(populated)

    assert service.decide(populated, p["id"], "aprovar", author="ana") == {"estado": "aprovada"}

    with populated.connect() as conn:
        alt = conn.execute(
            text("SELECT origem, proposta_id, autor, campo FROM curadoria.alteracao")
        ).one()
    assert tuple(alt) == ("llm", p["id"], "ana", "descricao")
    assert (
        scalar(populated, "SELECT descricao FROM analitico.conjunto_busca WHERE id = 'ds-0001'")
        == p["valor_proposto"]
    )
    assert proposals(populated, id=p["id"])[0]["decidida_por"] == "ana"


def test_editar_aplica_o_valor_do_humano_com_origem_humano(populated: Engine) -> None:
    p = first_proposal(populated)

    service.decide(
        populated,
        p["id"],
        "editar",
        author="ana",
        edited_value="Descrição ajustada pelo curador, completa e clara para o público em geral.",
    )

    with populated.connect() as conn:
        alt = conn.execute(text("SELECT origem, proposta_id FROM curadoria.alteracao")).one()
    assert tuple(alt) == ("humano", p["id"])
    assert proposals(populated, id=p["id"])[0]["estado"] == "editada"
    with pytest.raises(curation.CurationError):
        service.decide(
            populated, first_proposal(populated, ds="ds-0002")["id"], "editar", author="ana"
        )  # sem valor


def test_rejeitar_nao_altera_nada(populated: Engine) -> None:
    p = first_proposal(populated)

    assert service.decide(populated, p["id"], "rejeitar", author="ana") == {"estado": "rejeitada"}

    assert scalar(populated, "SELECT count(*) FROM curadoria.alteracao") == 0


def test_proposta_decidida_nao_pode_ser_decidida_de_novo(populated: Engine) -> None:
    p = first_proposal(populated)
    service.decide(populated, p["id"], "rejeitar", author="ana")

    with pytest.raises(ConflictError, match="rejeitada"):
        service.decide(populated, p["id"], "aprovar", author="ana")


def test_proposta_fica_desatualizada_se_um_humano_editou_antes(populated: Engine) -> None:
    p = first_proposal(populated)
    curation.apply_changes(
        populated,
        "ds-0001",
        {"descricao": "Outra descrição escrita por uma pessoa da equipe."},
        author="bia",
    )

    with pytest.raises(ConflictError, match="desatualizada"):
        service.decide(populated, p["id"], "aprovar", author="ana")

    assert (
        proposals(populated, id=p["id"])[0]["estado"] == "desatualizada"
    )  # marcação confirmada, não revertida
    assert scalar(populated, "SELECT count(*) FROM curadoria.alteracao") == 1  # só a edição humana


def test_proposta_fica_desatualizada_se_o_portal_mudou_o_conjunto(
    populated: Engine, portal: FakePortal
) -> None:
    p = first_proposal(populated)
    portal.update_title("ds-0001", "Título novo no portal")
    portal.datasets["ds-0001"]["descricao"] = (
        "Descrição nova publicada pelo órgão no portal de dados."
    )
    run_extraction(populated, portal, "incremental")

    assert proposals(populated, id=p["id"])[0]["estado"] == "desatualizada"
    with pytest.raises(ConflictError):
        service.decide(populated, p["id"], "aprovar", author="ana")


def test_decisao_invalida_e_proposta_inexistente(populated: Engine) -> None:
    with pytest.raises(curation.CurationError):
        service.decide(populated, 1, "talvez", author="ana")
    with pytest.raises(curation.NotFoundError):
        service.decide(populated, 999, "aprovar", author="ana")


def test_decisao_em_lote_ignora_o_que_nao_pode(populated: Engine) -> None:
    ex = make_execution(populated, "sugerir-tags", ["ds-0001", "ds-0002", "ds-0003"])
    run_all(populated)
    ids = [p["id"] for p in proposals(populated, execucao_id=ex)]
    service.decide(populated, ids[0], "rejeitar", author="ana")

    out = service.decide_bulk(populated, [*ids, 9999], "aprovar", author="ana")

    assert out == {"decididas": 2, "ignoradas": 2}
    with pytest.raises(curation.CurationError):
        service.decide_bulk(populated, ids, "editar", author="ana")


def test_tarefas_de_tags_e_tema_funcionam_ponta_a_ponta(populated: Engine) -> None:
    pt = first_proposal(populated, "sugerir-tags", "ds-saude")
    service.decide(populated, pt["id"], "aprovar", author="ana")
    assert (
        len(scalar(populated, "SELECT tags FROM analitico.conjunto_busca WHERE id = 'ds-saude'"))
        >= 3
    )  # type: ignore[arg-type]

    curation.apply_changes(
        populated,
        "ds-0003",
        {"titulo": "Indicadores de saúde e educação por município"},
        author="ana",
    )
    ptema = first_proposal(populated, "sugerir-tema", "ds-0003")
    assert set(ptema["valor_proposto"]) <= {"saude", "educacao", "trabalho"}


# ----------------------------------------------------------------- API


@pytest.fixture
def llm_api(populated: Engine) -> Iterator[TestClient]:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    app.dependency_overrides[get_settings] = lambda: SIM
    yield TestClient(app)


def test_api_estado_tarefas_e_desligado(populated: Engine) -> None:
    app = create_app()
    app.dependency_overrides[get_db] = lambda: populated
    off = TestClient(app)

    assert off.get("/v1/llm/estado").json()["habilitado"] is False
    r = off.post("/v1/llm/execucoes", json={"tarefa": "sugerir-tags", "ids": ["ds-0001"]})
    assert r.status_code == 409 and "desligado" in r.json()["detail"]


def test_api_fluxo_completo_com_o_provedor_simulado(llm_api: TestClient, populated: Engine) -> None:
    est = llm_api.get("/v1/llm/estado").json()
    assert (
        est["habilitado"]
        and est["simulado"]
        and not est["externo"]
        and est["limite_por_execucao"] == 200
    )
    assert {t["chave"] for t in llm_api.get("/v1/llm/tarefas").json()} == {
        "melhorar-descricao",
        "sugerir-tags",
        "sugerir-tema",
    }

    r = llm_api.post(
        "/v1/llm/execucoes",
        json={"tarefa": "melhorar-descricao", "ids": ["ds-0001", "ds-0002"]},
        headers={"X-Curador": "bruno"},
    )
    assert (
        r.status_code == 202
        and r.json()["estado"] == "enfileirada"
        and r.json()["solicitada_por"] == "bruno"
    )
    ex = r.json()["id"]
    assert (
        llm_api.post(
            "/v1/llm/execucoes", json={"tarefa": "sugerir-tags", "ids": ["ds-0003"]}
        ).status_code
        == 409
    )  # uma por vez

    run_all(populated)
    done = llm_api.get(f"/v1/llm/execucoes/{ex}").json()
    assert (
        done["estado"] == "concluida"
        and done["pendentes"] == 2
        and done["totais"]["propostas"] == 2
    )

    lista = llm_api.get("/v1/llm/propostas", params={"estado": "pendente"}).json()
    assert lista["total"] == 2 and lista["itens"][0]["conjunto_titulo"].startswith(
        "Conjunto ds-000"
    )
    pid = lista["itens"][0]["id"]
    assert "prompt" in llm_api.get(f"/v1/llm/propostas/{pid}").json()

    assert llm_api.post(
        f"/v1/llm/propostas/{pid}/decidir",
        json={"decisao": "aprovar"},
        headers={"X-Curador": "bruno"},
    ).json() == {"estado": "aprovada"}
    assert (
        llm_api.post(f"/v1/llm/propostas/{pid}/decidir", json={"decisao": "aprovar"}).status_code
        == 409
    )
    outra = lista["itens"][1]["id"]
    assert llm_api.post(
        "/v1/llm/propostas/decidir-em-lote", json={"ids": [outra], "decisao": "rejeitar"}
    ).json() == {"decididas": 1, "ignoradas": 0}
    assert (
        llm_api.get("/v1/conjuntos/" + lista["itens"][0]["conjunto_id"]).json()["alteracoes"][0][
            "origem"
        ]
        == "llm"
    )


def test_api_execucao_por_filtros_ids_ou_filtros_nao_ambos(
    llm_api: TestClient, populated: Engine
) -> None:
    assert llm_api.post("/v1/llm/execucoes", json={"tarefa": "sugerir-tags"}).status_code == 422
    assert (
        llm_api.post(
            "/v1/llm/execucoes",
            json={"tarefa": "sugerir-tags", "ids": ["a"], "filtros": {"tema": "saude"}},
        ).status_code
        == 422
    )
    r = llm_api.post(
        "/v1/llm/execucoes", json={"tarefa": "sugerir-tags", "filtros": {"organizacao": "orgao-1"}}
    )
    assert r.status_code == 202 and r.json()["conjuntos"] > 0
    assert llm_api.post(f"/v1/llm/execucoes/{r.json()['id']}/cancelar").json() == {
        "resultado": "cancelada"
    }
    assert llm_api.get("/v1/llm/execucoes/999").status_code == 404
    assert len(llm_api.get("/v1/llm/execucoes").json()) == 1
