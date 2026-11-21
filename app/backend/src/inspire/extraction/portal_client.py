"""Cliente HTTP do portal dados.gov.br: resiliente, educado e sem vazar a chave.

Comportamentos importantes, todos medidos no portal real:
- toda rota exige o header ``chave-api-dados-abertos``;
- a API é intermitente: a mesma consulta pode devolver lista vazia e logo depois dados. Por isso uma
  lista vazia só é aceita como "fim" depois de várias tentativas (``get_page``).
"""

from __future__ import annotations

import random
import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

import httpx
import structlog

from inspire import __version__
from inspire.extraction.errors import (
    PortalAuthError,
    PortalRequestError,
    PortalUnavailableError,
)

API_KEY_HEADER = "chave-api-dados-abertos"
USER_AGENT = f"inspire-catalogo/{__version__} (projeto Inspire; coleta de metadados)"
# O portal recusa chamadas em excesso com 405 (observado em 2026-11-21: 16.601 respostas 405 depois de ~3.500
# chamadas rápidas; os mesmos itens respondiam 200 minutos depois). Tratamos como bloqueio temporário.
THROTTLE_STATUS = frozenset({405, 408, 425, 429, 503})
RETRYABLE_STATUS = THROTTLE_STATUS | {500, 502, 504}
BAD_REQUEST_RETRIES = (
    2  # 400 às vezes é definitivo (item com defeito no portal), mas vale confirmar
)


@dataclass(frozen=True)
class Page:
    """Resultado de uma página de listagem.

    ``confirmed_empty`` é True quando a página continuou vazia depois de todas as tentativas, o que é o
    sinal de que acabaram os itens (e não de que a API falhou).
    """

    items: list[Any]
    confirmed_empty: bool


class PortalClient:
    def __init__(
        self,
        base_url: str,
        api_key: str,
        *,
        max_retries: int = 6,
        empty_retries: int = 4,
        backoff_base_s: float = 0.5,
        backoff_cap_s: float = 30.0,
        max_concurrency: int = 4,
        connect_timeout_s: float = 10.0,
        read_timeout_s: float = 30.0,
        max_rps: float = 0.0,
        throttle_cooldown_s: float = 5.0,
        throttle_cap_s: float = 120.0,
        clock: Callable[[], float] = time.monotonic,
        transport: httpx.BaseTransport | None = None,
        sleep: Callable[[float], None] = time.sleep,
        rng: Callable[[], float] = random.random,
    ) -> None:
        if not api_key:
            raise PortalAuthError("DADOS_GOV_API_KEY não configurada")
        self._max_retries = max_retries
        self._empty_retries = empty_retries
        self._backoff_base_s = backoff_base_s
        self._backoff_cap_s = backoff_cap_s
        self._sleep = sleep
        self._rng = rng
        self._clock = clock
        self._min_interval = 1.0 / max_rps if max_rps > 0 else 0.0
        self._cooldown_s = throttle_cooldown_s
        self._cooldown_cap_s = throttle_cap_s
        self._gate = threading.Lock()
        self._next_slot = 0.0
        self._blocked_until = 0.0
        self._throttle_streak = 0
        self._slots = threading.BoundedSemaphore(max_concurrency)
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"),
            headers={
                API_KEY_HEADER: api_key,
                "Accept": "application/json",
                "User-Agent": USER_AGENT,
            },
            timeout=httpx.Timeout(read_timeout_s, connect=connect_timeout_s),
            transport=transport,
        )

    def __repr__(self) -> str:  # nunca mostra a chave
        return f"PortalClient(base_url={str(self._http.base_url)!r})"

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> PortalClient:
        return self

    def __exit__(self, *_exc: object) -> None:
        self.close()

    # ------------------------------------------------------------------ API pública

    def get_json(self, path: str, params: Mapping[str, Any] | None = None) -> Any:
        """GET que devolve o JSON. Corpo vazio é tratado como falha transitória e tentado de novo."""
        body, _ = self._fetch(path, params, retries=self._max_retries, empty_is_final=False)
        return body

    def get_page(self, path: str, params: Mapping[str, Any] | None = None) -> Page:
        """GET de uma listagem. Lista vazia é tentada de novo antes de ser aceita como fim."""
        body, confirmed_empty = self._fetch(
            path, params, retries=self._max_retries, empty_is_final=True
        )
        if confirmed_empty:
            return Page(items=[], confirmed_empty=True)
        if not isinstance(body, list):
            raise PortalRequestError(f"Resposta inesperada em {path}: esperava uma lista")
        return Page(items=body, confirmed_empty=False)

    # ------------------------------------------------------------------ internos

    def _fetch(
        self,
        path: str,
        params: Mapping[str, Any] | None,
        *,
        retries: int,
        empty_is_final: bool,
    ) -> tuple[Any, bool]:
        log = structlog.get_logger("portal")
        empties = 0
        bad_requests = 0
        last_reason = "sem tentativas"
        for attempt in range(retries + 1):
            retry_after: float | None = None
            try:
                self._pace()
                with self._slots:
                    response = self._http.get(path, params=params)
            except httpx.TransportError as exc:  # timeout, conexão recusada, DNS…
                last_reason = type(exc).__name__
            else:
                status = response.status_code
                if status in (401, 403):
                    raise PortalAuthError(f"Portal recusou a chave (HTTP {status})")
                if status in RETRYABLE_STATUS:
                    last_reason = f"HTTP {status}"
                    retry_after = _parse_retry_after(response.headers.get("Retry-After"))
                    if status in THROTTLE_STATUS:
                        self._penalize(retry_after)
                elif status == 400 and bad_requests < BAD_REQUEST_RETRIES:
                    bad_requests += 1
                    last_reason = "HTTP 400"
                elif status >= 400:
                    raise PortalRequestError(
                        f"Pedido recusado pelo portal (HTTP {status}) em {path}",
                        status_code=status,
                    )
                else:
                    try:
                        body = response.json() if response.content else None
                    except ValueError:  # corpo cortado ou não-JSON: trata como falha transitória
                        last_reason = "JSON inválido"
                    else:
                        self._relax()
                        if body:  # lista ou objeto com conteúdo
                            return body, False
                        empties += 1
                        last_reason = "resposta vazia"
                        if empty_is_final and empties > self._empty_retries:
                            return [], True
            if attempt == retries:
                break
            delay = self._delay(attempt, retry_after)
            log.warning(
                "portal_nova_tentativa",
                caminho=path,
                tentativa=attempt + 1,
                motivo=last_reason,
                espera_s=round(delay, 2),
            )
            self._sleep(delay)
        raise PortalUnavailableError(
            f"Portal sem resposta utilizável em {path} ({last_reason})", attempts=retries + 1
        )

    def _pace(self) -> None:
        """Respeita o limite de requisições por segundo e a pausa coletiva depois de um bloqueio."""
        with self._gate:
            now = self._clock()
            start = max(now, self._next_slot, self._blocked_until)
            self._next_slot = start + self._min_interval
        if start > now:
            self._sleep(start - now)

    def _penalize(self, retry_after: float | None) -> None:
        """O portal pediu calma: todas as threads esperam, e a pausa cresce se o bloqueio insistir."""
        with self._gate:
            self._throttle_streak += 1
            cooldown = min(
                self._cooldown_cap_s, self._cooldown_s * 2.0 ** (self._throttle_streak - 1)
            )
            if retry_after is not None:
                cooldown = max(cooldown, min(retry_after, self._cooldown_cap_s))
            self._blocked_until = max(self._blocked_until, self._clock() + cooldown)

    def _relax(self) -> None:
        with self._gate:
            self._throttle_streak = 0

    def _delay(self, attempt: int, retry_after: float | None) -> float:
        ceiling = min(self._backoff_cap_s, self._backoff_base_s * (2.0**attempt))
        delay = ceiling / 2 + self._rng() * ceiling / 2  # jitter: entre 50% e 100% do teto
        if retry_after is not None:
            delay = max(delay, min(retry_after, self._backoff_cap_s))
        return delay


def _parse_retry_after(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return max(0.0, float(value))
    except ValueError:
        return None  # formato de data não é usado pelo portal; ignora
