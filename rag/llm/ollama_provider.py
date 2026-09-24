"""Ollama LLM provider.

Talks to a local Ollama HTTP API (default ``http://127.0.0.1:11434``).
Uses only the stdlib ``urllib.request`` so no extra dependencies are required.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from rag.llm.base import LLMProvider, LLMResponse
from rag.llm.cleanup import strip_thinking_sections

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "qwen2.5-coder:7b"
_DEFAULT_THINK = False
_REQUEST_TIMEOUT_SECONDS = 120


class OllamaProvider(LLMProvider):
    """LLM provider backed by a local Ollama server.

    ``think`` controls the model's extended thinking/reasoning phase via the
    Ollama API's top-level ``"think"`` request field (supported by Qwen3 and
    other thinking-capable models). It must be sent top-level, not inside
    ``options``, where Ollama silently ignores it. Disabled by default so
    grounded study answers are produced directly without a long thinking phase.
    """

    def __init__(
        self,
        *,
        base_url: str = _DEFAULT_BASE_URL,
        model: str = _DEFAULT_MODEL,
        timeout: int = _REQUEST_TIMEOUT_SECONDS,
        think: bool = _DEFAULT_THINK,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout = timeout
        self._think = think

    def _build_payload(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> dict:
        """Build the ``/api/chat`` request body for the configured model."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        return {
            "model": self._model,
            "messages": messages,
            "stream": False,
            "think": self._think,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        payload = self._build_payload(
            prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self._base_url}/api/chat",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                body = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            logger.warning("Ollama request failed: %s", exc)
            raise RuntimeError(
                "The language model is temporarily unavailable. "
                "Please try again later."
            ) from exc

        message = body.get("message", {})
        text = strip_thinking_sections(message.get("content", "")).strip()
        return LLMResponse(
            text=text,
            model=self._model,
            finish_reason="stop",
            usage={
                "prompt_tokens": body.get("prompt_eval_count", 0),
                "completion_tokens": body.get("eval_count", 0),
            },
        )

    def is_available(self) -> bool:
        try:
            req = urllib.request.Request(
                f"{self._base_url}/api/tags",
                method="GET",
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                return resp.status == 200
        except (urllib.error.URLError, TimeoutError, OSError):
            return False

    def close(self) -> None:
        pass
