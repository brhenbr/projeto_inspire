"""Provedores de LLM atrás de uma interface única (ADR-0011).

- `OpenAICompatibleProvider`: protocolo "chat completions" aceito por Ollama, vLLM, llama.cpp e muitos serviços.
- `SimulatedProvider`: SEM IA e sem rede; gera sugestões determinísticas por regras simples, só para o fluxo
  (selecionar, executar, revisar, aprovar, auditar) funcionar e poder ser demonstrado e testado offline.

Barreiras do ADR-0004: só chama hosts da lista permitida; a chave nunca aparece em log nem em `repr`.
"""

from __future__ import annotations

import json
import re
import time
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol
from urllib.parse import urlparse

import httpx
import structlog

from inspire.config import Settings

LOCAL_HOSTS = frozenset({"localhost", "127.0.0.1", "llm-local", "host.docker.internal"})
STOPWORDS = frozenset(
    [
        "para",
        "como",
        "pelo",
        "pela",
        "pelos",
        "pelas",
        "dados",
        "conjunto",
        "conjuntos",
        "sobre",
        "entre",
        "desde",
        "ate",
        "mais",
        "menos",
        "esta",
        "este",
        "esses",
        "essas",
        "isso",
        "aqui",
        "onde",
        "quando",
        "todos",
        "todas",
        "cada",
        "outro",
        "outra",
        "outros",
        "outras",
        "ainda",
        "tambem",
        "apenas",
        "brasil",
        "governo",
        "federal",
        "publico",
        "publica",
        "referente",
        "referentes",
        "relativo",
        "relativos",
    ]
)


class LlmError(Exception):
    """Falha ao obter resposta do provedor (rede, limite de uso, resposta inválida)."""


class LlmQuotaError(LlmError):
    """Limite de uso ou cota esgotada no provedor (HTTP 429/402); `retry_after_s` indica quando voltar."""

    def __init__(self, message: str, retry_after_s: float | None = None) -> None:
        super().__init__(message)
        self.retry_after_s = retry_after_s


class LlmAuthError(LlmError):
    """Credencial recusada pelo provedor (HTTP 401/403)."""


class LlmDisabledError(LlmError):
    """O recurso está desligado ou mal configurado."""


@dataclass(frozen=True)
class LlmRequest:
    system: str
    user: str
    task: str
    context: dict[str, Any] = field(default_factory=dict)  # só o provedor simulado usa


@dataclass(frozen=True)
class LlmResponse:
    text: str
    model: str
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    provider: str | None = None  # quem de fato respondeu (relevante no roteador)


@dataclass(frozen=True)
class ProviderInfo:
    nome: str
    modelo: str
    externo: bool
    simulado: bool
    host: str | None


class LlmProvider(Protocol):
    info: ProviderInfo

    def complete(self, request: LlmRequest) -> LlmResponse: ...


class OpenAICompatibleProvider:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        model: str,
        *,
        timeout_s: float = 60.0,
        max_retries: int = 3,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        name: str = "openai-compatible",
    ) -> None:
        host = urlparse(base_url).hostname or ""
        self.info = ProviderInfo(
            nome=name,
            modelo=model,
            externo=host not in LOCAL_HOSTS,
            simulado=False,
            host=host,
        )
        self._max_retries = max_retries
        self._sleep = sleep
        headers = {"Content-Type": "application/json", "User-Agent": "inspire-catalogo"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), headers=headers, timeout=timeout_s, transport=transport
        )
        self._model = model

    def __repr__(self) -> str:  # nunca mostra a chave
        return f"OpenAICompatibleProvider(host={self.info.host!r}, modelo={self._model!r})"

    def complete(self, request: LlmRequest) -> LlmResponse:
        payload = {
            "model": self._model,
            "temperature": 0.2,
            "messages": [
                {"role": "system", "content": request.system},
                {"role": "user", "content": request.user},
            ],
        }
        log = structlog.get_logger("llm")
        last = "sem tentativas"
        quota: LlmQuotaError | None = None
        for attempt in range(self._max_retries + 1):
            try:
                response = self._http.post("/chat/completions", json=payload)
            except httpx.TransportError as exc:
                last = type(exc).__name__
            else:
                if response.status_code in (401, 403):
                    raise LlmAuthError(
                        f"Provedor recusou a credencial (HTTP {response.status_code})"
                    )
                if response.status_code == 402:  # saldo/cota esgotados: esperar não adianta
                    raise LlmQuotaError("Provedor sem saldo ou cota (HTTP 402)", 3600.0)
                if response.status_code in (429, 500, 502, 503, 504):
                    last = f"HTTP {response.status_code}"
                    if response.status_code == 429:
                        quota = LlmQuotaError(
                            "Limite de uso do provedor atingido (HTTP 429)",
                            _retry_after(response),
                        )
                        if self._max_retries == 0 or (quota.retry_after_s or 0) > 30.0:
                            raise quota  # espera longa: quem chama decide (ex.: roteador troca de provedor)
                elif response.status_code >= 400:
                    raise LlmError(f"Provedor recusou o pedido (HTTP {response.status_code})")
                else:
                    return self._parse(response)
            if attempt < self._max_retries:
                delay = min(30.0, 2.0 * (2**attempt))
                log.warning(
                    "llm_nova_tentativa", tentativa=attempt + 1, motivo=last, espera_s=delay
                )
                self._sleep(delay)
        if quota is not None and last == "HTTP 429":
            raise quota
        raise LlmError(f"Provedor sem resposta utilizável ({last})")

    def _parse(self, response: httpx.Response) -> LlmResponse:
        try:
            body = response.json()
            text = body["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as exc:
            raise LlmError("Resposta do provedor fora do formato esperado") from exc
        usage = body.get("usage") or {}
        return LlmResponse(
            text=str(text),
            model=str(body.get("model") or self._model),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )


def _retry_after(response: httpx.Response) -> float | None:
    raw = response.headers.get("retry-after")
    try:
        return max(0.0, float(raw)) if raw is not None else None
    except ValueError:
        return None


def _words(text: str) -> list[str]:
    return [w for w in re.findall(r"[A-Za-zÀ-ÿ]{5,}", text.lower()) if w not in STOPWORDS]


class SimulatedProvider:
    """Sugestões por regras simples. NÃO é IA; existe para demonstrar e testar o fluxo sem enviar dado algum."""

    info = ProviderInfo(
        nome="simulado", modelo="regras-simples-v1", externo=False, simulado=True, host=None
    )

    def complete(self, request: LlmRequest) -> LlmResponse:
        c = request.context
        if request.task == "melhorar-descricao":
            out: dict[str, Any] = {"descricao": self._description(c)}
        elif request.task == "sugerir-tags":
            out = {"tags": self._tags(c)}
        elif request.task == "sugerir-tema":
            out = {"temas": self._themes(c)}
        elif request.task == "interpretar-pergunta":
            from inspire.llm.interpret import simulate

            out = simulate(c)
        else:
            raise LlmError(f"Tarefa desconhecida para o provedor simulado: {request.task}")
        return LlmResponse(text=json.dumps(out, ensure_ascii=False), model=self.info.modelo)

    @staticmethod
    def _description(c: dict[str, Any]) -> str:
        parts = [str(c.get("titulo") or "Conjunto de dados").rstrip(".") + "."]
        original = (c.get("descricao") or "").strip()
        if len(original) >= 40:
            parts.append(original if original.endswith(".") else original + ".")
        org = c.get("organizacao")
        temas = ", ".join(c.get("temas") or [])
        sentence = (
            f"Conjunto de dados publicado por {org}"
            if org
            else "Conjunto de dados publicado no portal de dados abertos"
        )
        if temas:
            sentence += f", no tema {temas}"
        if c.get("formatos"):
            sentence += f", disponível nos formatos {', '.join(c['formatos'])}"
        if c.get("periodicidade"):
            sentence += f", com atualização {str(c['periodicidade']).lower()}"
        parts.append(sentence + ".")
        if len(" ".join(parts)) < 100:
            parts.append("Consulte os recursos associados para acessar os dados e a documentação.")
        return " ".join(parts)

    @staticmethod
    def _tags(c: dict[str, Any]) -> list[str]:
        existing = list(c.get("tags") or [])
        counts = Counter(
            _words(f"{c.get('titulo') or ''} {c.get('titulo') or ''} {c.get('descricao') or ''}")
        )
        known = {t.lower() for t in existing}
        extra = [w.capitalize() for w, _ in counts.most_common(12) if w not in known]
        return (existing + extra)[:8]

    @staticmethod
    def _themes(c: dict[str, Any]) -> list[str]:
        text = f"{c.get('titulo') or ''} {c.get('descricao') or ''}".lower()
        hits = [
            t["slug"]
            for t in c.get("temas_disponiveis") or []
            if t["slug"].replace("-", " ") in text or t["titulo"].lower() in text
        ]
        return sorted(set(hits)) or list(c.get("temas") or [])


# ----------------------------------------------------------------- roteador (ADR-0014)

# Provedores com camada gratuita que falam o protocolo "chat completions". O nome na lista LLM_ROUTER_PROVIDERS
# É a aprovação do provedor (ADR-0004): o host vem fixo daqui, não do ambiente. Modelos podem ser trocados por
# LLM_ROUTER_MODELS, pois as camadas gratuitas mudam com frequência.
ROUTER_PRESETS: dict[str, tuple[str, str]] = {
    "groq": ("https://api.groq.com/openai/v1", "openai/gpt-oss-120b"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai", "gemini-3.5-flash"),
    "openrouter": ("https://openrouter.ai/api/v1", "nvidia/nemotron-3-ultra-550b-a55b:free"),
    "cerebras": ("https://api.cerebras.ai/v1", "gpt-oss-120b"),
    "mistral": ("https://api.mistral.ai/v1", "mistral-small-latest"),
    "deepseek": ("https://api.deepseek.com", "deepseek-chat"),
}
SHORT_COOLDOWN_S = 30.0  # falha transitória (rede, 5xx)
DEFAULT_QUOTA_COOLDOWN_S = 60.0  # 429 sem Retry-After
MAX_WAIT_S = 65.0  # se todos estão em pausa por menos que isso, espera; senão falha o item


class RouterProvider:
    """Tenta os provedores na ordem; ao estourar a cota (ou falhar) de um, pausa-o e usa o próximo."""

    def __init__(
        self,
        providers: list[LlmProvider],
        *,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        if not providers:
            raise LlmDisabledError("Nenhum provedor do roteador tem chave configurada")
        self._providers = providers
        self._blocked_until: dict[str, float] = {}
        self._clock = clock
        self._sleep = sleep
        self.info = ProviderInfo(
            nome="roteador",
            modelo="auto: " + ", ".join(p.info.nome for p in providers),
            externo=any(p.info.externo for p in providers),
            simulado=False,
            host=", ".join(str(p.info.host) for p in providers),
        )

    def estado(self) -> list[dict[str, Any]]:
        now = self._clock()
        return [
            {
                "provedor": p.info.nome,
                "modelo": p.info.modelo,
                "em_pausa_s": max(0.0, round(self._blocked_until.get(p.info.nome, 0.0) - now, 1)),
            }
            for p in self._providers
        ]

    def complete(self, request: LlmRequest) -> LlmResponse:
        log = structlog.get_logger("llm")
        errors: list[str] = []
        for _ in range(2):  # a segunda volta só ocorre depois de uma espera curta
            tried = 0
            for p in self._providers:
                name = p.info.nome
                if self._blocked_until.get(name, 0.0) > self._clock():
                    continue
                tried += 1
                try:
                    response = p.complete(request)
                except LlmQuotaError as exc:
                    wait = (
                        exc.retry_after_s
                        if exc.retry_after_s is not None
                        else DEFAULT_QUOTA_COOLDOWN_S
                    )
                    self._blocked_until[name] = self._clock() + wait
                    errors.append(f"{name}: cota")
                    log.warning("llm_roteador_cota", provedor=name, pausa_s=wait)
                except LlmAuthError:
                    self._blocked_until[name] = self._clock() + 86400.0
                    errors.append(f"{name}: credencial recusada")
                    log.error("llm_roteador_credencial", provedor=name)
                except LlmError as exc:
                    errors.append(f"{name}: {exc}")
                    if "fora do formato" not in str(exc) and "recusou o pedido" not in str(exc):
                        self._blocked_until[name] = self._clock() + SHORT_COOLDOWN_S
                else:
                    return LlmResponse(
                        text=response.text,
                        model=response.model,
                        prompt_tokens=response.prompt_tokens,
                        completion_tokens=response.completion_tokens,
                        provider=name,
                    )
            if tried:
                break  # havia provedores disponíveis e todos falharam: não insistir
            earliest = (
                min(self._blocked_until.get(p.info.nome, 0.0) for p in self._providers)
                - self._clock()
            )
            if earliest > MAX_WAIT_S:
                break
            self._sleep(max(0.0, earliest))
        detail = "; ".join(errors or ["todos em pausa por cota"])
        raise LlmError(f"Todos os provedores indisponíveis agora ({detail})")


def build_provider(settings: Settings) -> LlmProvider:
    """Cria o provedor configurado, aplicando as barreiras do ADR-0004."""
    if not settings.llm_enabled:
        raise LlmDisabledError("O recurso de LLM está desligado (LLM_ENABLED=false)")
    if settings.llm_provider == "simulado":
        return SimulatedProvider()
    if settings.llm_provider == "roteador":
        return _cached_router(settings)
    if settings.llm_provider != "openai-compatible":
        raise LlmDisabledError(f"Provedor de LLM desconhecido: {settings.llm_provider}")
    host = urlparse(settings.llm_base_url).hostname or ""
    allowed = {h.strip().lower() for h in settings.llm_allowed_hosts.split(",") if h.strip()}
    if not host or host.lower() not in allowed:
        raise LlmDisabledError(
            f"Host '{host}' não está na lista de provedores aprovados (LLM_ALLOWED_HOSTS). "
            "Nenhuma chamada foi feita."
        )
    if not settings.llm_model:
        raise LlmDisabledError("LLM_MODEL não configurado")
    return OpenAICompatibleProvider(
        settings.llm_base_url,
        settings.llm_api_key.get_secret_value(),
        settings.llm_model,
        timeout_s=settings.llm_timeout_s,
    )


def describe(settings: Settings) -> dict[str, Any]:
    """Estado do recurso para a tela (inclui o aviso de provedor externo, ADR-0004 item 5)."""
    try:
        info = build_provider(settings).info
    except LlmDisabledError as exc:
        return {
            "habilitado": False,
            "motivo": str(exc),
            "externo": False,
            "simulado": False,
            "provedor": None,
            "modelo": None,
        }
    return {
        "habilitado": True,
        "motivo": None,
        "externo": info.externo,
        "simulado": info.simulado,
        "provedor": info.nome,
        "modelo": info.modelo,
        "host": info.host,
    }


def build_router(settings: Settings) -> RouterProvider:
    names = [n.strip().lower() for n in settings.llm_router_providers.split(",") if n.strip()]
    unknown = [n for n in names if n not in ROUTER_PRESETS]
    if unknown:
        raise LlmDisabledError(f"Provedor desconhecido no roteador: {', '.join(unknown)}")
    keys = {n: k.get_secret_value() for n, k in settings.router_keys().items()}
    built: list[LlmProvider] = []
    for name in names:
        key = keys.get(name, "")
        if not key:
            continue  # sem chave: o provedor é ignorado (não é erro)
        base_url, default_model = ROUTER_PRESETS[name]
        model = settings.router_models().get(name) or default_model
        built.append(
            OpenAICompatibleProvider(
                base_url, key, model, timeout_s=settings.llm_timeout_s, max_retries=0, name=name
            )
        )
    return RouterProvider(built)


_ROUTER_CACHE: dict[str, Any] = {}


def _cached_router(settings: Settings) -> RouterProvider:
    """Um roteador por configuração e por processo, para a pausa por cota valer entre as chamadas da API."""
    if _ROUTER_CACHE.get("settings") is not settings:
        _ROUTER_CACHE["settings"] = settings
        _ROUTER_CACHE["router"] = build_router(settings)
    router: RouterProvider = _ROUTER_CACHE["router"]
    return router
