"""Ollama LLM provider.

Talks to a local Ollama HTTP API (default ``http://127.0.0.1:11434``).
Uses only the stdlib ``urllib.request`` so no extra dependencies are required.
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from rag.llm.base import (
    LLMProvider,
    LLMRequestError,
    LLMResponse,
    LLMTimeoutError,
    LLMUnavailableError,
)
from rag.llm.cleanup import strip_thinking_sections

logger = logging.getLogger(__name__)

_DEFAULT_BASE_URL = "http://127.0.0.1:11434"
_DEFAULT_MODEL = "qwen2.5-coder:7b"
_DEFAULT_THINK = False

# Must comfortably exceed the wall-clock time a local CPU-only model needs for a
# long answer. qwen2.5-coder:7b runs at roughly 3 tokens/sec on CPU, so a
# 1100-token (10-mark) answer needs ~190s and a 1600-token (20-mark) answer
# ~230s. The previous 120s default could not finish either and surfaced as a
# spurious "temporarily unavailable".
_REQUEST_TIMEOUT_SECONDS = 300

_UNAVAILABLE_MESSAGE = (
    "The language model is temporarily unavailable. Please try again later."
)

# Body of an Ollama HTTP error is JSON like {"error": "model not found"}.
# Read defensively: it may be empty, truncated, or not JSON at all.
_MAX_ERROR_BODY_BYTES = 512


def _describe_http_error(exc: urllib.error.HTTPError) -> str:
    """Return a short, safe description of an Ollama HTTP error response."""
    try:
        raw = exc.read()[:_MAX_ERROR_BODY_BYTES].decode("utf-8", errors="replace")
    except Exception:  # pragma: no cover - defensive, body already consumed
        return "<unreadable body>"
    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        return raw.strip() or "<empty body>"
    if isinstance(parsed, dict) and isinstance(parsed.get("error"), str):
        return parsed["error"].strip() or "<empty error>"
    return raw.strip() or "<empty body>"


def _is_timeout(exc: BaseException) -> bool:
    """True when *exc* (or a ``URLError`` it wraps) represents a timeout."""
    if isinstance(exc, TimeoutError):
        return True
    reason = getattr(exc, "reason", None)
    if isinstance(reason, TimeoutError):
        return True
    return "timed out" in str(exc).lower()


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
                raw_body = resp.read().decode("utf-8")
        except urllib.error.HTTPError as exc:
            # Checked first: HTTPError subclasses URLError, and a 404 (unknown
            # model) must not masquerade as a transient outage.
            detail = _describe_http_error(exc)
            logger.error(
                "Ollama rejected request: HTTP %s for model %r at %s: %s",
                exc.code,
                self._model,
                self._base_url,
                detail,
            )
            raise LLMRequestError(
                f"The language model rejected the request (HTTP {exc.code}). "
                "Please check the configured model."
            ) from exc
        except urllib.error.URLError as exc:
            if _is_timeout(exc):
                logger.error(
                    "Ollama generation timed out after %ss (model=%r, base_url=%s). "
                    "The model is reachable but too slow: raise LLM_TIMEOUT_SECONDS "
                    "or lower the generation budget.",
                    self._timeout,
                    self._model,
                    self._base_url,
                )
                raise LLMTimeoutError(
                    f"The language model took longer than {self._timeout}s to "
                    "answer. Please try a shorter answer."
                ) from exc
            logger.warning(
                "Could not reach Ollama at %s: %s", self._base_url, exc
            )
            raise LLMUnavailableError(_UNAVAILABLE_MESSAGE) from exc
        except TimeoutError as exc:
            logger.error(
                "Ollama generation timed out after %ss (model=%r, base_url=%s). "
                "The model is reachable but too slow: raise LLM_TIMEOUT_SECONDS "
                "or lower the generation budget.",
                self._timeout,
                self._model,
                self._base_url,
            )
            raise LLMTimeoutError(
                f"The language model took longer than {self._timeout}s to answer. "
                "Please try a shorter answer."
            ) from exc
        except OSError as exc:
            logger.warning("Ollama request failed at %s: %s", self._base_url, exc)
            raise LLMUnavailableError(_UNAVAILABLE_MESSAGE) from exc

        try:
            body = json.loads(raw_body)
        except (json.JSONDecodeError, UnicodeDecodeError) as exc:
            logger.error(
                "Ollama returned a non-JSON body for model %r: %.200r",
                self._model,
                raw_body,
            )
            raise LLMRequestError(
                "The language model returned an unreadable response."
            ) from exc

        if not isinstance(body, dict):
            logger.error(
                "Ollama returned a non-object body for model %r: %.200r",
                self._model,
                raw_body,
            )
            raise LLMRequestError(
                "The language model returned an unreadable response."
            )

        message = body.get("message", {})
        if not isinstance(message, dict):
            logger.error(
                "Ollama response for model %r has no usable message field: %.200r",
                self._model,
                raw_body,
            )
            raise LLMRequestError(
                "The language model returned an unreadable response."
            )

        text = strip_thinking_sections(message.get("content", "") or "").strip()
        if not text:
            # An empty completion is a generation failure. Returning it as an
            # empty answer would let callers present it as a real answer.
            logger.warning(
                "Ollama returned an empty completion for model %r "
                "(done_reason=%r, prompt_tokens=%r, completion_tokens=%r)",
                self._model,
                body.get("done_reason"),
                body.get("prompt_eval_count"),
                body.get("eval_count"),
            )
            raise LLMRequestError(
                "The language model returned an empty response."
            )

        return LLMResponse(
            text=text,
            model=self._model,
            finish_reason=str(body.get("done_reason") or "stop"),
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
