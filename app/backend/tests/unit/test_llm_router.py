import httpx
import pytest

from inspire.config import Settings
from inspire.llm import providers
from inspire.llm.providers import (
    LlmAuthError,
    LlmDisabledError,
    LlmError,
    LlmQuotaError,
    LlmRequest,
    LlmResponse,
    OpenAICompatibleProvider,
    ProviderInfo,
    RouterProvider,
)

REQ = LlmRequest(system="s", user="u", task="sugerir-tags")


class Fake:
    def __init__(self, name: str, behaviour: object) -> None:
        self.info = ProviderInfo(
            nome=name, modelo="m", externo=True, simulado=False, host=f"{name}.x"
        )
        self.behaviour = behaviour
        self.calls = 0

    def complete(self, request: LlmRequest) -> LlmResponse:
        self.calls += 1
        if isinstance(self.behaviour, Exception):
            raise self.behaviour
        return LlmResponse(text="ok", model="m")


class Clock:
    def __init__(self) -> None:
        self.now = 0.0
        self.slept: list[float] = []

    def __call__(self) -> float:
        return self.now

    def sleep(self, s: float) -> None:
        self.slept.append(s)
        self.now += s


def router(*ps: Fake, clock: Clock | None = None) -> RouterProvider:
    c = clock or Clock()
    return RouterProvider(list(ps), clock=c, sleep=c.sleep)


def test_uses_first_provider_and_reports_who_answered() -> None:
    a, b = Fake("a", None), Fake("b", None)
    assert router(a, b).complete(REQ).provider == "a"
    assert b.calls == 0


def test_quota_moves_to_next_and_pauses_the_exhausted_one() -> None:
    a, b = Fake("a", LlmQuotaError("cota", 120.0)), Fake("b", None)
    r = router(a, b)
    assert r.complete(REQ).provider == "b"
    assert r.complete(REQ).provider == "b"
    assert a.calls == 1  # em pausa: não foi chamado de novo
    assert r.estado()[0]["em_pausa_s"] == 120.0


def test_provider_returns_after_pause_ends() -> None:
    clock = Clock()
    a, b = Fake("a", LlmQuotaError("cota", 10.0)), Fake("b", None)
    r = router(a, b, clock=clock)
    r.complete(REQ)
    clock.now = 11.0
    a.behaviour = None
    assert r.complete(REQ).provider == "a"


def test_invalid_credential_disables_provider_for_a_day() -> None:
    a, b = Fake("a", LlmAuthError("nao")), Fake("b", None)
    r = router(a, b)
    r.complete(REQ)
    assert r.estado()[0]["em_pausa_s"] >= 86000


def test_all_in_short_pause_waits_then_succeeds() -> None:
    clock = Clock()
    a = Fake("a", LlmQuotaError("cota", 20.0))
    r = router(a, clock=clock)
    with pytest.raises(LlmError):
        r.complete(REQ)  # primeira chamada: a falha e fica em pausa
    a.behaviour = None
    assert r.complete(REQ).provider == "a"
    assert clock.slept == [20.0]


def test_all_in_long_pause_fails_without_waiting() -> None:
    clock = Clock()
    r = router(Fake("a", LlmQuotaError("cota", 3600.0)), clock=clock)
    with pytest.raises(LlmError):
        r.complete(REQ)
    with pytest.raises(LlmError, match="indisponíveis"):
        r.complete(REQ)
    assert clock.slept == []


def test_transient_error_pauses_briefly_and_falls_back() -> None:
    a, b = Fake("a", LlmError("Provedor sem resposta utilizável (HTTP 503)")), Fake("b", None)
    r = router(a, b)
    assert r.complete(REQ).provider == "b"
    assert 0 < r.estado()[0]["em_pausa_s"] <= 30


def test_empty_router_is_disabled() -> None:
    with pytest.raises(LlmDisabledError):
        RouterProvider([])


def http_provider(status: int, headers: dict[str, str] | None = None) -> OpenAICompatibleProvider:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status, headers=headers or {}, json={})

    return OpenAICompatibleProvider(
        "https://api.exemplo.org/v1",
        "k",
        "m",
        max_retries=0,
        transport=httpx.MockTransport(handler),
    )


def test_http_429_becomes_quota_error_with_retry_after() -> None:
    with pytest.raises(LlmQuotaError) as exc:
        http_provider(429, {"retry-after": "42"}).complete(REQ)
    assert exc.value.retry_after_s == 42.0


def test_http_402_is_quota_and_401_is_auth() -> None:
    with pytest.raises(LlmQuotaError):
        http_provider(402).complete(REQ)
    with pytest.raises(LlmAuthError):
        http_provider(401).complete(REQ)


def settings(**kw: str) -> Settings:
    return Settings(llm_enabled=True, llm_provider="roteador", **kw)  # type: ignore[arg-type]


def test_build_router_ignores_providers_without_key_and_uses_fixed_hosts() -> None:
    r = providers.build_provider(
        settings(llm_router_providers="groq,gemini", groq_api_key="segredo-groq")  # type: ignore[arg-type]
    )
    assert isinstance(r, RouterProvider)
    assert r.info.host == "api.groq.com"
    assert "segredo-groq" not in repr(r.info) + repr(r.estado())


def test_build_router_without_any_key_is_disabled_and_unknown_name_rejected() -> None:
    with pytest.raises(LlmDisabledError):
        providers.build_provider(settings(llm_router_providers="groq"))
    with pytest.raises(LlmDisabledError, match="desconhecido"):
        providers.build_provider(settings(llm_router_providers="exemplo", groq_api_key="x"))  # type: ignore[arg-type]
