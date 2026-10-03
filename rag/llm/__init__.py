"""LLM provider abstraction for the RAG answer engine.

Provides a common :class:`LLMProvider` interface, an :class:`OllamaProvider`
that talks to a local Ollama HTTP API, and a :class:`MockProvider` for tests.

Provider failures are raised as typed :class:`LLMError` subclasses
(:class:`LLMTimeoutError`, :class:`LLMUnavailableError`,
:class:`LLMRequestError`) so callers can distinguish a slow model from an
unreachable backend from a bad request.
"""

from rag.llm.base import (
    LLMError,
    LLMProvider,
    LLMRequestError,
    LLMResponse,
    LLMTimeoutError,
    LLMUnavailableError,
)
from rag.llm.mock_provider import MockProvider
from rag.llm.ollama_provider import OllamaProvider

__all__ = [
    "LLMError",
    "LLMProvider",
    "LLMRequestError",
    "LLMResponse",
    "LLMTimeoutError",
    "LLMUnavailableError",
    "MockProvider",
    "OllamaProvider",
]
