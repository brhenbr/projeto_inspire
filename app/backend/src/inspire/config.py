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

    # LLM externo: desligado por padrão (ADR-0004)
    llm_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
