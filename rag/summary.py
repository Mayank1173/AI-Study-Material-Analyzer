"""RAG study-summary service: grounded subject summaries from existing material.

This module composes the same building blocks as :mod:`rag.answer`
(owner-scoped search -> context builder -> LLM provider) to produce a subject
summary grounded exclusively in the student's own indexed material, without
duplicating the RAG pipeline. It enforces the same guarantees as the chat
engine:

- **Ownership**: retrieval is always scoped to the authenticated user; a
  ``course_id`` filter can only narrow that set, never broaden it.
- **Grounding**: the summary prompt forces output from retrieved material only.
- **No-context behaviour**: when no indexed material exists, a clear message is
  returned instead of a hallucination.
- **Prompt-injection defence**: retrieved text is wrapped as data, not
  instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rag.answer import AnswerSource, sources_from_results
from rag.context_builder import build_summary_prompt
from rag.knowledge_base import KnowledgeBase
from rag.llm.base import LLMProvider, LLMResponse
from rag.llm.cleanup import strip_thinking_sections
from rag.models import SearchResult

DEFAULT_SUMMARY_TOP_K = 12

_RETRIEVAL_HINT = "key topics, concepts, definitions, and connections"

_NO_CONTEXT_SUMMARY = (
    "No processed study material was found to summarize yet. "
    "Upload and process study material for the subject first, "
    "then request the study summary again."
)

_LLM_UNAVAILABLE_SUMMARY = (
    "The language model is temporarily unavailable. "
    "Please try again later."
)

_FALLBACK_SUMMARY = (
    "The study summary could not be generated from the retrieved material "
    "right now. Please try again."
)


@dataclass(frozen=True)
class SummaryResult:
    """Complete study summary returned by the RAG summary service."""

    summary: str
    sources: list[AnswerSource] = field(default_factory=list)
    has_context: bool = True
    model: str = ""


def _retrieval_query(subject_name: str | None) -> str:
    """Build the semantic search query used to gather summary material."""
    if subject_name and subject_name.strip():
        return f"{subject_name.strip()} ({_RETRIEVAL_HINT})"
    return _RETRIEVAL_HINT


def generate_study_summary(
    knowledge_base: KnowledgeBase,
    llm: LLMProvider,
    *,
    user_id: str,
    course_id: str | None = None,
    subject_name: str | None = None,
    top_k: int = DEFAULT_SUMMARY_TOP_K,
) -> SummaryResult:
    """Generate a study summary grounded in the user's indexed study material.

    Parameters
    ----------
    knowledge_base:
        The Phase 2 searchable index.
    llm:
        The LLM provider for text generation.
    user_id:
        **Authenticated** user id (never taken from the client).
    course_id:
        Optional course scope used to gather the subject's material. It can
        only narrow the authenticated user's own index.
    subject_name:
        Optional human-readable subject label (e.g. the course name) used to
        steer retrieval and label the prompt. Never a source of facts.
    top_k:
        Number of chunks to gather for the summary.

    Returns
    -------
    SummaryResult
        The grounded summary with source references.
    """
    results: list[SearchResult] = knowledge_base.search(
        _retrieval_query(subject_name),
        user_id=user_id,
        course_id=course_id,
        top_k=top_k,
    )

    sources = sources_from_results(results)

    if not results:
        return SummaryResult(
            summary=_NO_CONTEXT_SUMMARY,
            sources=[],
            has_context=False,
        )

    system_prompt, user_prompt = build_summary_prompt(subject_name, results)

    try:
        response: LLMResponse = llm.generate(
            user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=2048,
        )
    except Exception:
        return SummaryResult(
            summary=_LLM_UNAVAILABLE_SUMMARY,
            sources=sources,
            has_context=True,
            model="",
        )

    summary = strip_thinking_sections(response.text).strip()
    if not summary:
        summary = _FALLBACK_SUMMARY

    return SummaryResult(
        summary=summary,
        sources=sources,
        has_context=True,
        model=response.model,
    )