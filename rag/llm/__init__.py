"""LLM provider abstraction for the RAG answer engine.

Provides a common :class:`LLMProvider` interface, an :class:`OllamaProvider`
that talks to a local Ollama HTTP API, and a :class:`MockProvider` for tests.
"""

from rag.llm.base import LLMProvider, LLMResponse
from rag.llm.mock_provider import MockProvider
from rag.llm.ollama_provider import OllamaProvider

__all__ = [
    "LLMProvider",
    "LLMResponse",
    "MockProvider",
    "OllamaProvider",
]
