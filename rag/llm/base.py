"""Abstract LLM provider interface.

Every provider produces an :class:`LLMResponse` containing the generated text
and optional metadata (model name, token counts).  Providers must never leak
internal paths, API keys, or infrastructure details in error messages.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


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
