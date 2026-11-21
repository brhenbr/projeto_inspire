"""Configuração lida do ambiente. Segredos usam SecretStr para não vazar em logs ou repr."""

from functools import lru_cache

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=None, extra="ignore")

    database_url: str = "postgresql+psycopg://inspire:inspire_dev@db:5432/inspire"
    log_level: str = "INFO"

    # Portal dados.gov.br (usado só pelo worker)
    dados_gov_base_url: str = "https://dados.gov.br"
    dados_gov_api_key: SecretStr = SecretStr("")

    # Boas maneiras com o portal (ADR-0006): concorrência baixa, timeouts explícitos, retry com backoff.
    portal_max_concurrency: int = 4
    portal_connect_timeout_s: float = 10.0
    portal_read_timeout_s: float = 30.0
    portal_max_retries: int = 6
    portal_empty_retries: int = 4
    portal_backoff_base_s: float = 0.5
    portal_backoff_cap_s: float = 30.0
    portal_max_rps: float = 4.0  # o portal bloqueia (HTTP 405) quando chamado rápido demais
    portal_throttle_cooldown_s: float = 5.0
    portal_throttle_cap_s: float = 120.0

    # Controle de pedidos de extração (ADR-0006)
    extraction_min_interval_incremental_min: int = 60
    extraction_min_interval_full_min: int = 1440
    extraction_failure_wait_min: int = 5

    # LLM (ADR-0004 e ADR-0011): desligado por padrão; só hosts da lista; campos públicos apenas
    llm_enabled: bool = False
    llm_provider: str = "simulado"  # 'simulado' (sem IA, sem rede) ou 'openai-compatible'
    llm_base_url: str = ""
    llm_api_key: SecretStr = SecretStr("")
    llm_model: str = ""
    llm_allowed_hosts: str = "localhost,127.0.0.1,llm-local"
    llm_timeout_s: float = 60.0
    llm_request_interval_s: float = 1.0


@lru_cache
def get_settings() -> Settings:
    return Settings()
