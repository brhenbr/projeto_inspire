import json

import httpx
import pytest

from inspire.config import Settings
from inspire.llm import providers, tasks
from inspire.llm.providers import (
    LlmDisabledError,
    LlmError,
    LlmRequest,
    OpenAICompatibleProvider,
    SimulatedProvider,
)

KEY = "chave-llm-secreta"


def ok_body(content: str) -> dict:  # type: ignore[type-arg]
    return {
        "model": "modelo-x",
        "choices": [{"message": {"content": content}}],
        "usage": {"prompt_tokens": 5, "completion_tokens": 7},
    }


def make(handler, **kw):  # type: ignore[no-untyped-def]
    sleeps: list[float] = []
    return OpenAICompatibleProvider(
        "https://llm.exemplo.org/v1",
        KEY,
        "modelo-x",
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        **kw,
    ), sleeps


REQ = LlmRequest(system="s", user="u", task="sugerir-tags")


# ----------------------------------------------------------------- provedor compatível com OpenAI


def test_envia_mensagens_e_le_resposta_e_uso() -> None:
    seen: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request)
        return httpx.Response(200, json=ok_body('{"tags": ["a"]}'))

    provider, _ = make(handler)
    out = provider.complete(REQ)

    body = json.loads(seen[0].content)
    assert (
        seen[0].url.path == "/v1/chat/completions"
        and seen[0].headers["Authorization"] == f"Bearer {KEY}"
    )
    assert body["model"] == "modelo-x" and [m["role"] for m in body["messages"]] == [
        "system",
        "user",
    ]
    assert out.text == '{"tags": ["a"]}' and out.model == "modelo-x" and out.completion_tokens == 7


def test_chave_nunca_aparece_no_repr() -> None:
    provider, _ = make(lambda r: httpx.Response(200, json=ok_body("{}")))

    assert KEY not in repr(provider) and "llm.exemplo.org" in repr(provider)


def test_host_externo_e_marcado_como_externo_e_local_nao() -> None:
    ext, _ = make(lambda r: httpx.Response(200))
    local = OpenAICompatibleProvider("http://localhost:11434/v1", "", "m")

    assert ext.info.externo is True and local.info.externo is False


@pytest.mark.parametrize("status", [401, 403])
def test_credencial_recusada_nao_tenta_de_novo(status: int) -> None:
    calls = []
    provider, sleeps = make(lambda r: (calls.append(1), httpx.Response(status))[1])

    with pytest.raises(LlmError, match="credencial"):
        provider.complete(REQ)

    assert len(calls) == 1 and sleeps == []


def test_limite_de_uso_e_tentado_de_novo_com_espera() -> None:
    answers = iter(
        [httpx.Response(429), httpx.Response(503), httpx.Response(200, json=ok_body("{}"))]
    )
    provider, sleeps = make(lambda r: next(answers))

    assert provider.complete(REQ).text == "{}"
    assert sleeps == [2.0, 4.0]


def test_desiste_depois_das_tentativas() -> None:
    provider, _ = make(lambda r: httpx.Response(503), max_retries=2)

    with pytest.raises(LlmError, match="sem resposta"):
        provider.complete(REQ)


@pytest.mark.parametrize("payload", [{}, {"choices": []}, {"choices": [{"message": {}}]}, "texto"])
def test_resposta_fora_do_formato_vira_erro(payload: object) -> None:
    provider, _ = make(lambda r: httpx.Response(200, json=payload))

    with pytest.raises(LlmError, match="formato"):
        provider.complete(REQ)


# ----------------------------------------------------------------- barreiras do ADR-0004


def test_desligado_por_padrao() -> None:
    with pytest.raises(LlmDisabledError, match="desligado"):
        providers.build_provider(Settings())


def test_host_fora_da_lista_aprovada_e_recusado_sem_nenhuma_chamada() -> None:
    s = Settings(
        llm_enabled=True,
        llm_provider="openai-compatible",
        llm_base_url="https://api.exemplo.com/v1",
        llm_model="m",
    )

    with pytest.raises(LlmDisabledError, match="não está na lista"):
        providers.build_provider(s)


def test_host_aprovado_e_aceito_e_a_lista_e_configuravel() -> None:
    s = Settings(
        llm_enabled=True,
        llm_provider="openai-compatible",
        llm_base_url="https://api.exemplo.com/v1",
        llm_model="m",
        llm_allowed_hosts="localhost, api.exemplo.com",
    )

    provider = providers.build_provider(s)

    assert provider.info.externo is True and provider.info.host == "api.exemplo.com"


def test_provedor_local_e_aceito_por_padrao() -> None:
    s = Settings(
        llm_enabled=True,
        llm_provider="openai-compatible",
        llm_base_url="http://llm-local:8000/v1",
        llm_model="m",
    )

    assert providers.build_provider(s).info.externo is False


def test_modelo_e_obrigatorio_e_provedor_desconhecido_e_recusado() -> None:
    with pytest.raises(LlmDisabledError, match="LLM_MODEL"):
        providers.build_provider(
            Settings(
                llm_enabled=True,
                llm_provider="openai-compatible",
                llm_base_url="http://localhost/v1",
            )
        )
    with pytest.raises(LlmDisabledError, match="desconhecido"):
        providers.build_provider(Settings(llm_enabled=True, llm_provider="outro"))


def test_estado_para_a_tela_avisa_quando_externo_ou_simulado() -> None:
    assert providers.describe(Settings())["habilitado"] is False
    sim = providers.describe(Settings(llm_enabled=True))
    assert sim["habilitado"] and sim["simulado"] and not sim["externo"]
    ext = providers.describe(
        Settings(
            llm_enabled=True,
            llm_provider="openai-compatible",
            llm_base_url="https://a.com/v1",
            llm_model="m",
            llm_allowed_hosts="a.com",
        )
    )
    assert ext["externo"] is True and ext["host"] == "a.com"


# ----------------------------------------------------------------- contexto público


def test_contexto_so_aceita_campos_publicos() -> None:
    tasks.assert_public({"titulo": "x", "tags": [], "temas_disponiveis": []})
    for forbidden in ("emailResponsavel", "responsavel", "id", "recursos", "link"):
        with pytest.raises(tasks.PrivacyViolationError):
            tasks.assert_public({"titulo": "x", forbidden: "segredo"})


def test_render_inclui_instrucoes_do_curador_limitadas() -> None:
    ctx = {
        "titulo": "T",
        "descricao": "D",
        "tags": [],
        "temas": [],
        "organizacao": "O",
        "formatos": ["CSV"],
        "licenca": None,
        "periodicidade": None,
    }
    task = tasks.TASKS_BY_KEY["melhorar-descricao"]

    system, user = tasks.render(task, ctx, "Use tom formal. " + "x" * 2000)

    assert "Título: T" in user and "(não informado)" in user and "Use tom formal" in user
    assert len(user) < len(task.prompt_usuario) + tasks.MAX_INSTRUCTIONS + 400 and "JSON" in system


def test_render_recusa_contexto_com_campo_proibido() -> None:
    with pytest.raises(tasks.PrivacyViolationError):
        tasks.render(tasks.TASKS[0], {"titulo": "x", "emailResponsavel": "a@b.gov.br"})


def test_chaves_com_chaves_no_texto_nao_quebram_o_template() -> None:
    ctx = {
        "titulo": "Dados {x} e {{y}}",
        "descricao": "{0}",
        "tags": [],
        "temas": [],
        "organizacao": "{}",
        "formatos": [],
        "licenca": None,
        "periodicidade": None,
    }

    _, user = tasks.render(tasks.TASKS_BY_KEY["sugerir-tags"], ctx)

    assert "Dados {x} e {{y}}" in user


# ----------------------------------------------------------------- validação da saída (não confiável)


def test_extrai_json_de_cercas_de_codigo_e_texto_em_volta() -> None:
    assert tasks.extract_json('```json\n{"a": 1}\n```') == {"a": 1}
    assert tasks.extract_json('Claro! Aqui está: {"a": 1} Espero ter ajudado.') == {"a": 1}


@pytest.mark.parametrize("raw", ["", "sem json", "{quebrado", "[1, 2]", '{"a": '])
def test_saida_sem_json_valido_e_recusada(raw: str) -> None:
    with pytest.raises(ValueError):
        tasks.extract_json(raw)


def test_descricao_valida_e_limites() -> None:
    ok = json.dumps({"descricao": "  " + "texto bom " * 8 + "  "})
    assert tasks.parse_output("melhorar-descricao", ok, {}, set()).startswith("texto bom")
    for bad in (
        '{"descricao": "curta"}',
        '{"descricao": 5}',
        "{}",
        json.dumps({"descricao": "x" * 2001}),
    ):
        with pytest.raises(ValueError):
            tasks.parse_output("melhorar-descricao", bad, {}, set())


def test_tags_sao_mescladas_com_as_existentes_e_limpas() -> None:
    out = tasks.parse_output(
        "sugerir-tags", '{"tags": ["Saúde", " saúde ", "", "x"]}', {"tags": ["antiga"]}, set()
    )

    assert out == sorted({"Saúde", "saúde", "x", "antiga"})
    with pytest.raises(ValueError):
        tasks.parse_output("sugerir-tags", '{"tags": []}', {}, set())
    with pytest.raises(ValueError):
        tasks.parse_output("sugerir-tags", '{"tags": [1]}', {}, set())


def test_tema_precisa_estar_na_lista_oficial() -> None:
    assert tasks.parse_output("sugerir-tema", '{"temas": ["saude", "saude"]}', {}, {"saude"}) == [
        "saude"
    ]
    with pytest.raises(ValueError, match="fora da lista"):
        tasks.parse_output("sugerir-tema", '{"temas": ["inventado"]}', {}, {"saude"})
    with pytest.raises(ValueError):
        tasks.parse_output("sugerir-tema", '{"temas": []}', {}, {"saude"})


def test_tarefa_desconhecida() -> None:
    with pytest.raises(ValueError):
        tasks.parse_output("outra", "{}", {}, set())


# ----------------------------------------------------------------- provedor simulado


CTX = {
    "titulo": "Execução orçamentária da União",
    "descricao": "",
    "tags": ["Orçamento"],
    "temas": [],
    "organizacao": "Ministério da Economia",
    "formatos": ["CSV"],
    "licenca": "cc-by",
    "periodicidade": "MENSAL",
    "temas_disponiveis": [
        {"slug": "economia", "titulo": "Economia"},
        {"slug": "saude", "titulo": "Saúde"},
    ],
}


def run_sim(task: str, ctx: dict) -> dict:  # type: ignore[type-arg]
    return json.loads(SimulatedProvider().complete(LlmRequest("s", "u", task, ctx)).text)


def test_simulado_nao_e_ia_e_se_declara_simulado() -> None:
    info = SimulatedProvider.info

    assert info.simulado and not info.externo and info.host is None


def test_simulado_gera_descricao_valida_para_a_validacao() -> None:
    raw = SimulatedProvider().complete(LlmRequest("s", "u", "melhorar-descricao", CTX)).text

    out = tasks.parse_output("melhorar-descricao", raw, CTX, set())

    assert "Ministério da Economia" in out and "CSV" in out and len(out) >= 100


def test_simulado_sugere_tags_novas_sem_perder_as_existentes() -> None:
    ctx = {
        **CTX,
        "titulo": "Orçamento federal executado por unidade gestora",
        "descricao": "Execução orçamentária mensal detalhada",
    }

    tags = run_sim("sugerir-tags", ctx)["tags"]

    assert "Orçamento" in tags and len(tags) > 1 and len(tags) <= 8


def test_simulado_escolhe_tema_pelo_texto_ou_mantem_o_atual() -> None:
    assert run_sim("sugerir-tema", {**CTX, "titulo": "Indicadores de saúde", "temas": []})[
        "temas"
    ] == ["saude"]
    assert run_sim("sugerir-tema", {**CTX, "titulo": "Nada a ver", "temas": ["economia"]})[
        "temas"
    ] == ["economia"]


def test_simulado_recusa_tarefa_desconhecida() -> None:
    with pytest.raises(LlmError):
        SimulatedProvider().complete(LlmRequest("s", "u", "x", {}))
