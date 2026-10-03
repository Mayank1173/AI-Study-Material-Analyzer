"""Abstract LLM provider interface.

Every provider produces an :class:`LLMResponse` containing the generated text
and optional metadata (model name, token counts).  Providers must never leak
internal paths, API keys, or infrastructure details in error messages.

Failures are reported through the typed errors below rather than a single
generic ``RuntimeError``, so callers can react correctly to each kind:

- :class:`LLMTimeoutError`: generation exceeded the client's timeout. The model
  was reachable but too slow. This is **not** an availability problem, and must
  never be reported as "temporarily unavailable".
- :class:`LLMUnavailableError`: the backend could not be reached at all
  (connection refused, server down). Genuinely "temporarily unavailable".
- :class:`LLMRequestError`: the backend answered but rejected the request
  (unknown model, bad request) or returned an unreadable body. This is a
  configuration problem and will not fix itself by retrying.

All three subclass :class:`LLMError` (itself a ``RuntimeError``), so existing
``except RuntimeError`` handlers keep working.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


class LLMError(RuntimeError):
    """Base class for every LLM provider failure."""


class LLMTimeoutError(LLMError):
    """Generation exceeded the configured timeout.

    The provider was reachable and accepted the request; it simply did not
    finish in time. Distinct from :class:`LLMUnavailableError` because the
    remedy is a longer timeout or a smaller generation budget, not a retry.
    """


class LLMUnavailableError(LLMError):
    """The LLM backend could not be reached."""


class LLMRequestError(LLMError):
    """The LLM backend rejected the request or replied with an unusable body.

    Usually a configuration problem (for example an unknown model name), so it
    is surfaced as an error instead of being retried indefinitely.
    """


@dataclass(frozen=True)
class LLMResponse:
    """Structured output from an LLM provider."""

    text: str
    model: str = ""
    finish_reason: str = "stop"
    usage: dict[str, int] = field(default_factory=dict)


class LLMProvider(ABC):
    """Base class for all LLM backends."""

    @abstractmethod
    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        """Generate a completion from *prompt*.

        Parameters
        ----------
        prompt:
            The user / context prompt.
        system_prompt:
            Optional system-level instruction prepended by the provider.
        temperature:
            Sampling temperature (0 = deterministic).
        max_tokens:
            Maximum tokens in the generated response.
        """

    @abstractmethod
    def is_available(self) -> bool:
        """Return ``True`` if the backend is reachable (best-effort)."""

    def close(self) -> None:
        """Release resources; safe to call multiple times."""
