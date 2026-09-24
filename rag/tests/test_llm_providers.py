"""Tests for the LLM provider abstraction layer."""

from __future__ import annotations

import json
import urllib.error
from unittest import mock

import pytest

from rag.llm.base import LLMProvider, LLMResponse
from rag.llm.mock_provider import MockProvider
from rag.llm.ollama_provider import OllamaProvider


class TestLLMResponse:
    def test_default_values(self) -> None:
        resp = LLMResponse(text="hello")
        assert resp.text == "hello"
        assert resp.model == ""
        assert resp.finish_reason == "stop"
        assert resp.usage == {}

    def test_custom_values(self) -> None:
        resp = LLMResponse(
            text="answer",
            model="test-model",
            finish_reason="length",
            usage={"prompt_tokens": 10, "completion_tokens": 5},
        )
        assert resp.model == "test-model"
        assert resp.finish_reason == "length"
        assert resp.usage["prompt_tokens"] == 10

    def test_frozen(self) -> None:
        resp = LLMResponse(text="x")
        with pytest.raises(AttributeError):
            resp.text = "y"  # type: ignore[misc]


class TestMockProvider:
    def test_returns_default_answer(self) -> None:
        llm = MockProvider()
        resp = llm.generate("What is photosynthesis?")
        assert resp.text == "This is a mock answer based on the provided context."
        assert resp.model == "mock-model"

    def test_keyword_matching(self) -> None:
        llm = MockProvider(
            keyword_answers={
                "photosynthesis": "Plants convert light to energy.",
                "gravity": "Objects attract each other.",
            }
        )
        resp = llm.generate("Tell me about photosynthesis")
        assert resp.text == "Plants convert light to energy."

    def test_keyword_case_insensitive(self) -> None:
        llm = MockProvider(keyword_answers={"PHOTOSYNTHESIS": "Answer"})
        resp = llm.generate("What is Photosynthesis?")
        assert resp.text == "Answer"

    def test_no_match_returns_default(self) -> None:
        llm = MockProvider(keyword_answers={"physics": "Force equals mass times acceleration."})
        resp = llm.generate("Tell me about chemistry")
        assert resp.text == "This is a mock answer based on the provided context."

    def test_tracks_call_count(self) -> None:
        llm = MockProvider()
        assert llm.call_count == 0
        llm.generate("first")
        assert llm.call_count == 1
        llm.generate("second")
        assert llm.call_count == 2

    def test_records_last_prompt(self) -> None:
        llm = MockProvider()
        llm.generate("What is 2+2?")
        assert llm.last_prompt == "What is 2+2?"

    def test_records_system_prompt(self) -> None:
        llm = MockProvider()
        llm.generate("test", system_prompt="Be helpful")
        assert llm.last_system_prompt == "Be helpful"

    def test_is_always_available(self) -> None:
        llm = MockProvider()
        assert llm.is_available() is True

    def test_close_is_safe(self) -> None:
        llm = MockProvider()
        llm.close()

    def test_implements_interface(self) -> None:
        llm = MockProvider()
        assert isinstance(llm, LLMProvider)

    def test_custom_default_answer(self) -> None:
        llm = MockProvider(default_answer="custom default")
        resp = llm.generate("anything")
        assert resp.text == "custom default"

    def test_empty_keyword_matches(self) -> None:
        llm = MockProvider(keyword_answers={})
        resp = llm.generate("any query")
        assert resp.text == "This is a mock answer based on the provided context."

    def test_usage_always_zero(self) -> None:
        llm = MockProvider()
        resp = llm.generate("test")
        assert resp.usage == {"prompt_tokens": 0, "completion_tokens": 0}


class TestOllamaProviderConfig:
    def test_default_model_is_installed_local_model(self) -> None:
        llm = OllamaProvider()
        assert llm._model == "qwen2.5-coder:7b"

    def test_custom_model_is_preserved(self) -> None:
        llm = OllamaProvider(model="qwen3:4b")
        assert llm._model == "qwen3:4b"

    def test_model_override_does_not_change_base_url(self) -> None:
        llm = OllamaProvider(
            model="qwen3-agent:latest",
            base_url="http://localhost:11435",
        )
        assert llm._model == "qwen3-agent:latest"
        assert llm._base_url == "http://localhost:11435"

    def test_implements_interface(self) -> None:
        llm = OllamaProvider()
        assert isinstance(llm, LLMProvider)

    def test_close_is_safe_without_server(self) -> None:
        llm = OllamaProvider()
        llm.close()

    def test_think_disabled_by_default(self) -> None:
        llm = OllamaProvider()
        assert llm._think is False

    def test_think_can_be_enabled(self) -> None:
        llm = OllamaProvider(think=True)
        assert llm._think is True

    def test_timeout_default_is_generous_for_local_models(self) -> None:
        llm = OllamaProvider()
        assert llm._timeout == 120

    def test_timeout_is_configurable(self) -> None:
        llm = OllamaProvider(timeout=45)
        assert llm._timeout == 45

    def test_model_custom_keeps_default_think_and_timeout(self) -> None:
        llm = OllamaProvider(model="qwen3:4b")
        assert llm._model == "qwen3:4b"
        assert llm._think is False
        assert llm._timeout == 120


class TestOllamaRequestPayload:
    def test_payload_disables_thinking_by_default(self) -> None:
        payload = OllamaProvider()._build_payload("Who is Newton?")
        assert payload["think"] is False
        assert payload["stream"] is False
        assert payload["model"] == "qwen2.5-coder:7b"

    def test_payload_honors_explicit_think_enable(self) -> None:
        payload = OllamaProvider(think=True)._build_payload("Who is Newton?")
        assert payload["think"] is True

    def test_payload_sends_think_top_level_not_in_options(self) -> None:
        payload = OllamaProvider()._build_payload("Who is Newton?")
        assert "think" not in payload["options"]
        assert "think" in payload

    def test_payload_includes_messages_and_sampling_options(self) -> None:
        payload = OllamaProvider(model="qwen3-agent:latest")._build_payload(
            "Summarize", system_prompt="Use only the material.", temperature=0.2, max_tokens=512
        )
        assert payload["messages"] == [
            {"role": "system", "content": "Use only the material."},
            {"role": "user", "content": "Summarize"},
        ]
        assert payload["options"]["temperature"] == 0.2
        assert payload["options"]["num_predict"] == 512

    def test_no_system_prompt_means_single_user_message(self) -> None:
        payload = OllamaProvider()._build_payload("Hi")
        assert len(payload["messages"]) == 1
        assert payload["messages"][0]["role"] == "user"


class TestOllamaHTTPBehavior:
    def _fake_response(self) -> "mock.Mock":
        body = json.dumps(
            {
                "message": {"content": "Physics studies matter."},
                "prompt_eval_count": 8,
                "eval_count": 4,
            }
        ).encode("utf-8")
        resp = mock.Mock()
        resp.__enter__ = mock.Mock(return_value=resp)
        resp.__exit__ = mock.Mock(return_value=False)
        resp.read.return_value = body
        return resp

    def _sent_payload(self, urlopen_mock: "mock.Mock") -> dict:
        request = urlopen_mock.call_args.args[0]
        return json.loads(request.data.decode("utf-8"))

    def test_generate_sends_expected_payload(self) -> None:
        resp = self._fake_response()
        with mock.patch("urllib.request.urlopen", return_value=resp) as urlopen:
            llm = OllamaProvider()
            result = llm.generate("Who is Newton?", temperature=0.1)
        payload = self._sent_payload(urlopen)
        assert payload["model"] == "qwen2.5-coder:7b"
        assert payload["think"] is False
        assert payload["options"]["temperature"] == 0.1
        assert urlopen.call_args.kwargs["timeout"] == 120
        assert result.text == "Physics studies matter."
        assert result.model == "qwen2.5-coder:7b"
        assert result.usage["completion_tokens"] == 4

    def test_generate_uses_configured_timeout(self) -> None:
        resp = self._fake_response()
        with mock.patch("urllib.request.urlopen", return_value=resp) as urlopen:
            OllamaProvider(timeout=5).generate("Quick")
        assert urlopen.call_args.kwargs["timeout"] == 5

    def test_generate_strips_qwen_thinking_content(self) -> None:
        body = json.dumps(
            {
                "message": {
                    "content": (
                        "thinking\ninternal reasoning only\n/thinking\n"
                        "response\nThe student-visible answer.\n/response"
                    )
                },
                "prompt_eval_count": 8,
                "eval_count": 4,
            }
        ).encode("utf-8")
        resp = mock.Mock()
        resp.__enter__ = mock.Mock(return_value=resp)
        resp.__exit__ = mock.Mock(return_value=False)
        resp.read.return_value = body

        with mock.patch("urllib.request.urlopen", return_value=resp):
            result = OllamaProvider().generate("Hi")

        assert result.text == "The student-visible answer."
        assert "internal reasoning" not in result.text

    def test_generate_leaves_normal_content_unchanged(self) -> None:
        resp = self._fake_response()
        with mock.patch("urllib.request.urlopen", return_value=resp):
            result = OllamaProvider().generate("Hi")
        assert result.text == "Physics studies matter."

    def test_timeout_raises_safe_runtime_error(self) -> None:
        with mock.patch(
            "urllib.request.urlopen", side_effect=TimeoutError("timed out")
        ):
            with pytest.raises(RuntimeError) as exc_info:
                OllamaProvider().generate("Hi")
        assert "temporarily unavailable" in str(exc_info.value)

    def test_urlerror_raises_safe_runtime_error(self) -> None:
        with mock.patch(
            "urllib.request.urlopen",
            side_effect=urllib.error.URLError("connection refused"),
        ):
            with pytest.raises(RuntimeError) as exc_info:
                OllamaProvider().generate("Hi")
        assert "temporarily unavailable" in str(exc_info.value)
