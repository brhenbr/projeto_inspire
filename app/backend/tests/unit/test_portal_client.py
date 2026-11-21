import threading
import time
from collections.abc import Callable

import httpx
import pytest
import structlog
import structlog.testing

from inspire.extraction.errors import (
    PortalAuthError,
    PortalRequestError,
    PortalUnavailableError,
)
from inspire.extraction.portal_client import API_KEY_HEADER, USER_AGENT, PortalClient

KEY = "chave-secreta-123"
Handler = Callable[[httpx.Request], httpx.Response]


def make_client(handler: Handler, **kwargs: object) -> tuple[PortalClient, list[float]]:
    sleeps: list[float] = []
    client = PortalClient(
        "https://portal.test",
        KEY,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        rng=lambda: 1.0,  # sem aleatoriedade: espera = teto do backoff
        **kwargs,  # type: ignore[arg-type]
    )
    return client, sleeps


def sequence(*responses: httpx.Response | Exception) -> tuple[Handler, list[httpx.Request]]:
    """Handler que devolve as respostas em ordem (a última se repete)."""
    calls: list[httpx.Request] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        item = responses[min(len(calls) - 1, len(responses) - 1)]
        if isinstance(item, Exception):
            raise item
        return item

    return handler, calls


def ok(body: object) -> httpx.Response:
    return httpx.Response(200, json=body)


# ----------------------------------------------------------------- identificação e segredo


def test_envia_a_chave_e_um_user_agent_identificado() -> None:
    handler, calls = sequence(ok({"id": "1"}))
    client, _ = make_client(handler)

    client.get_json("/dados/api/publico/conjuntos-dados/1")

    assert calls[0].headers[API_KEY_HEADER] == KEY
    assert calls[0].headers["User-Agent"] == USER_AGENT
    assert "inspire-catalogo" in USER_AGENT


def test_sem_chave_nao_cria_o_cliente() -> None:
    with pytest.raises(PortalAuthError):
        PortalClient("https://portal.test", "")


def test_a_chave_nao_aparece_no_repr() -> None:
    client, _ = make_client(sequence(ok({"a": 1}))[0])

    assert KEY not in repr(client)


def test_a_chave_nao_aparece_nos_logs_de_retry() -> None:
    handler, _ = sequence(httpx.Response(503), ok({"a": 1}))
    client, _ = make_client(handler)

    with structlog.testing.capture_logs() as logs:
        client.get_json("/x")

    assert logs, "esperava um log de nova tentativa"
    assert KEY not in str(logs)


# ----------------------------------------------------------------- erros definitivos


@pytest.mark.parametrize("status", [401, 403])
def test_chave_recusada_nao_tenta_de_novo(status: int) -> None:
    handler, calls = sequence(httpx.Response(status))
    client, sleeps = make_client(handler)

    with pytest.raises(PortalAuthError):
        client.get_json("/x")

    assert len(calls) == 1
    assert sleeps == []


def test_outro_4xx_nao_tenta_de_novo() -> None:
    handler, calls = sequence(httpx.Response(400, json={"erro": "pagina invalida"}))
    client, _ = make_client(handler)

    with pytest.raises(PortalRequestError) as info:
        client.get_json("/x")

    assert len(calls) == 1
    assert info.value.status_code == 400  # quem coleta decide: item indisponível, segue em frente


# ----------------------------------------------------------------- retry


@pytest.mark.parametrize("status", [429, 500, 502, 503, 504])
def test_tenta_de_novo_em_erros_transitorios(status: int) -> None:
    handler, calls = sequence(httpx.Response(status), httpx.Response(status), ok({"id": "1"}))
    client, sleeps = make_client(handler, backoff_base_s=1.0)

    assert client.get_json("/x") == {"id": "1"}

    assert len(calls) == 3
    assert sleeps == [1.0, 2.0]  # backoff exponencial


def test_tenta_de_novo_em_timeout_e_falha_de_conexao() -> None:
    handler, calls = sequence(
        httpx.ReadTimeout("lento"), httpx.ConnectError("caiu"), ok({"id": "1"})
    )
    client, _ = make_client(handler)

    assert client.get_json("/x") == {"id": "1"}
    assert len(calls) == 3


def test_json_invalido_e_tratado_como_falha_transitoria() -> None:
    handler, calls = sequence(httpx.Response(200, content=b"{cortado"), ok({"id": "1"}))
    client, _ = make_client(handler)

    assert client.get_json("/x") == {"id": "1"}
    assert len(calls) == 2


def test_respeita_retry_after_do_portal() -> None:
    handler, _ = sequence(httpx.Response(429, headers={"Retry-After": "7"}), ok({"id": "1"}))
    client, sleeps = make_client(handler, backoff_base_s=0.5, backoff_cap_s=30.0)

    client.get_json("/x")

    assert sleeps == [7.0]


def test_espera_nunca_passa_do_teto() -> None:
    handler, _ = sequence(httpx.Response(503))
    client, sleeps = make_client(handler, max_retries=8, backoff_base_s=1.0, backoff_cap_s=5.0)

    with pytest.raises(PortalUnavailableError):
        client.get_json("/x")

    assert max(sleeps) == 5.0
    assert sleeps[:3] == [1.0, 2.0, 4.0]


def test_jitter_fica_entre_metade_e_o_teto() -> None:
    handler, _ = sequence(httpx.Response(503), ok({"a": 1}))
    sleeps: list[float] = []
    client = PortalClient(
        "https://portal.test",
        KEY,
        transport=httpx.MockTransport(handler),
        sleep=sleeps.append,
        rng=lambda: 0.0,
        backoff_base_s=4.0,
    )

    client.get_json("/x")

    assert sleeps == [2.0]  # com rng=0, metade do teto de 4 s


def test_desiste_depois_das_tentativas_e_informa_quantas_foram() -> None:
    handler, calls = sequence(httpx.Response(503))
    client, _ = make_client(handler, max_retries=3)

    with pytest.raises(PortalUnavailableError) as info:
        client.get_json("/x")

    assert len(calls) == 4
    assert info.value.attempts == 4


# ----------------------------------------------------------------- respostas vazias intermitentes


def test_detalhe_vazio_e_tentado_de_novo() -> None:
    handler, calls = sequence(ok({}), ok({}), ok({"id": "1"}))
    client, _ = make_client(handler)

    assert client.get_json("/x") == {"id": "1"}
    assert len(calls) == 3


def test_detalhe_sempre_vazio_vira_erro_e_nao_dado_perdido_em_silencio() -> None:
    handler, _ = sequence(ok({}))
    client, _ = make_client(handler, max_retries=2)

    with pytest.raises(PortalUnavailableError):
        client.get_json("/x")


def test_pagina_vazia_intermitente_nao_e_o_fim() -> None:
    itens = [{"id": str(n)} for n in range(15)]
    handler, calls = sequence(ok([]), ok([]), ok(itens))
    client, _ = make_client(handler)

    page = client.get_page("/conjuntos-dados", {"pagina": 7})

    assert page.items == itens
    assert page.confirmed_empty is False
    assert len(calls) == 3


def test_pagina_continuamente_vazia_e_confirmada_como_fim() -> None:
    handler, calls = sequence(ok([]))
    client, _ = make_client(handler, empty_retries=4)

    page = client.get_page("/conjuntos-dados", {"pagina": 2000})

    assert page.items == []
    assert page.confirmed_empty is True
    assert len(calls) == 5  # 1 tentativa + 4 repetições


def test_envia_os_parametros_da_consulta() -> None:
    handler, calls = sequence(ok([{"id": "1"}]))
    client, _ = make_client(handler)

    client.get_page("/dados/api/publico/conjuntos-dados", {"pagina": 3})

    assert calls[0].url.params["pagina"] == "3"


def test_resposta_de_listagem_que_nao_e_lista_e_erro() -> None:
    handler, _ = sequence(ok({"erro": "x"}))
    client, _ = make_client(handler)

    with pytest.raises(PortalRequestError):
        client.get_page("/x")


# ----------------------------------------------------------------- boas maneiras


def test_nunca_passa_do_limite_de_chamadas_simultaneas() -> None:
    limite = 3
    ativos = 0
    pico = 0
    lock = threading.Lock()

    def handler(_request: httpx.Request) -> httpx.Response:
        nonlocal ativos, pico
        with lock:
            ativos += 1
            pico = max(pico, ativos)
        time.sleep(0.02)
        with lock:
            ativos -= 1
        return ok({"id": "1"})

    client, _ = make_client(handler, max_concurrency=limite)
    threads = [threading.Thread(target=client.get_json, args=("/x",)) for _ in range(12)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert 1 <= pico <= limite
