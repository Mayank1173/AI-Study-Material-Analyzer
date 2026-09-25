"""Tests for the backend LLM configuration.

Verifies the defaults for the Ollama model, thinking mode and request timeout,
and that ``get_llm_provider`` passes all configured values to the provider. No
real Ollama server is required: constructing an OllamaProvider is a pure local
operation.
"""

from __future__ import annotations

from app.api.routes.chat import get_llm_provider
from app.core.config import get_settings
from rag.llm.ollama_provider import OllamaProvider


class TestDefaultModelConfig:
    def test_default_llm_model_is_installed_local_model(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("LLM_MODEL", raising=False)
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.llm_model == "qwen2.5-coder:7b"
        get_settings.cache_clear()

    def test_configured_model_is_read_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_MODEL", "qwen3:4b")
        get_settings.cache_clear()
        settings = get_settings()
        assert settings.llm_model == "qwen3:4b"
        get_settings.cache_clear()


class TestThinkingConfig:
    def test_default_think_is_disabled(self, monkeypatch) -> None:
        monkeypatch.delenv("LLM_THINK", raising=False)
        get_settings.cache_clear()
        assert get_settings().llm_think is False
        get_settings.cache_clear()

    def test_think_enabled_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_THINK", "true")
        get_settings.cache_clear()
        assert get_settings().llm_think is True
        get_settings.cache_clear()

    def test_invalid_think_value_reads_as_false(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_THINK", "maybe")
        get_settings.cache_clear()
        assert get_settings().llm_think is False
        get_settings.cache_clear()


class TestTimeoutConfig:
    def test_default_timeout_is_sensible_for_local_models(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
        get_settings.cache_clear()
        assert get_settings().llm_timeout_seconds == 120
        get_settings.cache_clear()

    def test_timeout_is_read_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "45")
        get_settings.cache_clear()
        assert get_settings().llm_timeout_seconds == 45
        get_settings.cache_clear()


class TestMaxTokensConfig:
    def test_default_max_tokens_is_bounded_for_local_models(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("LLM_MAX_TOKENS", raising=False)
        get_settings.cache_clear()
        tokens = get_settings().llm_max_tokens
        assert tokens <= 512
        get_settings.cache_clear()

    def test_max_tokens_is_read_from_env(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_MAX_TOKENS", "768")
        get_settings.cache_clear()
        assert get_settings().llm_max_tokens == 768
        get_settings.cache_clear()


class TestProviderChain:
    def test_provider_receives_configured_default_model(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("LLM_MODEL", raising=False)
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        get_settings.cache_clear()
        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)
        assert provider._model == "qwen2.5-coder:7b"
        get_settings.cache_clear()

    def test_provider_receives_custom_model(self, monkeypatch) -> None:
        monkeypatch.setenv("LLM_MODEL", "qwen3-agent:latest")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        get_settings.cache_clear()
        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)
        assert provider._model == "qwen3-agent:latest"
        get_settings.cache_clear()

    def test_provider_receives_default_think_and_timeout(
        self, monkeypatch
    ) -> None:
        monkeypatch.delenv("LLM_THINK", raising=False)
        monkeypatch.delenv("LLM_TIMEOUT_SECONDS", raising=False)
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        get_settings.cache_clear()
        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)
        assert provider._think is False
        assert provider._timeout == 120
        get_settings.cache_clear()

    def test_provider_receives_configured_think_and_timeout(
        self, monkeypatch
    ) -> None:
        monkeypatch.setenv("LLM_THINK", "true")
        monkeypatch.setenv("LLM_TIMEOUT_SECONDS", "60")
        monkeypatch.setenv("LLM_PROVIDER", "ollama")
        get_settings.cache_clear()
        provider = get_llm_provider()
        assert isinstance(provider, OllamaProvider)
        assert provider._think is True
        assert provider._timeout == 60
        get_settings.cache_clear()