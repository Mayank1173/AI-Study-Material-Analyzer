"""Deterministic mock LLM provider for tests.

Returns canned responses based on simple keyword matching so the full RAG
pipeline can be tested without any live LLM service.
"""

from __future__ import annotations

from rag.llm.base import LLMProvider, LLMResponse


class MockProvider(LLMProvider):
    """Deterministic LLM stub that returns pre-configured answers.

    Parameters
    ----------
    default_answer:
        Returned when no keyword match is found.
    keyword_answers:
        Mapping of lowercase keyword -> answer text.
    """

    NO_CONTEXT_ANSWER = (
        "I don't have enough information in your study materials to answer "
        "that question. Please upload relevant documents or try rephrasing."
    )

    def __init__(
        self,
        *,
        default_answer: str = "This is a mock answer based on the provided context.",
        keyword_answers: dict[str, str] | None = None,
    ) -> None:
        self._default_answer = default_answer
        self._keyword_answers = keyword_answers or {}
        self._call_count = 0
        self._last_prompt: str = ""
        self._last_system_prompt: str | None = None
        self._last_max_tokens: int = 0

    def generate(
        self,
        prompt: str,
        *,
        system_prompt: str | None = None,
        temperature: float = 0.3,
        max_tokens: int = 1024,
    ) -> LLMResponse:
        self._call_count += 1
        self._last_prompt = prompt
        self._last_system_prompt = system_prompt
        self._last_max_tokens = max_tokens

        prompt_lower = prompt.lower()
        for keyword, answer in self._keyword_answers.items():
            if keyword.lower() in prompt_lower:
                return LLMResponse(
                    text=answer,
                    model="mock-model",
                    finish_reason="stop",
                    usage={"prompt_tokens": 0, "completion_tokens": 0},
                )

        return LLMResponse(
            text=self._default_answer,
            model="mock-model",
            finish_reason="stop",
            usage={"prompt_tokens": 0, "completion_tokens": 0},
        )

    def is_available(self) -> bool:
        return True

    @property
    def call_count(self) -> int:
        return self._call_count

    @property
    def last_prompt(self) -> str:
        return self._last_prompt

    @property
    def last_system_prompt(self) -> str | None:
        return self._last_system_prompt

    @property
    def last_max_tokens(self) -> int:
        return self._last_max_tokens
