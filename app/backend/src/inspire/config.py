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

    # LLM externo: desligado por padrão (ADR-0004)
    llm_enabled: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
