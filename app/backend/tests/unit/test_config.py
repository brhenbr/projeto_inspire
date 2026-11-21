from inspire.config import Settings


def test_api_key_is_never_exposed_in_repr_or_str() -> None:
    settings = Settings(dados_gov_api_key="segredo-super-secreto")  # type: ignore[arg-type]

    assert "segredo-super-secreto" not in repr(settings)
    assert "segredo-super-secreto" not in str(settings)
    assert settings.dados_gov_api_key.get_secret_value() == "segredo-super-secreto"


def test_llm_is_disabled_by_default() -> None:
    assert Settings().llm_enabled is False


def test_settings_read_environment(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("LLM_ENABLED", "true")

    settings = Settings()

    assert settings.log_level == "DEBUG"
    assert settings.llm_enabled is True
