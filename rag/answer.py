"""RAG answer service: orchestrates search -> context -> LLM -> answer.

This module ties together the Phase 2 knowledge base search with the Phase 3
LLM provider through the context builder.  It enforces:

- **Ownership**: search is always scoped to the authenticated user.
- **Context, not a cage**: retrieved material is passed to the model as extra
  context, and the model answers with its own general knowledge as well. When
  nothing relevant is retrieved the model is still asked the question.
- **Prompt-injection defence**: retrieved text is wrapped as data, not instructions.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rag.context_builder import (
    ConversationTurn,
    build_grounded_prompt,
)
from rag.knowledge_base import KnowledgeBase
from rag.llm.base import LLMProvider, LLMResponse
from rag.llm.cleanup import strip_thinking_sections
from rag.models import SearchResult


@dataclass(frozen=True)
class AnswerSource:
    """Public-facing source reference attached to an answer."""

    source_index: int
    material_id: str
    course_id: str
    material_title: str | None = None
    original_filename: str | None = None
    source_location: str | None = None
    score: float = 0.0


@dataclass(frozen=True)
class AnswerResult:
    """Complete answer returned by the RAG engine."""

    answer: str
    sources: list[AnswerSource] = field(default_factory=list)
    has_context: bool = True
    model: str = ""


def sources_from_results(results: list[SearchResult]) -> list[AnswerSource]:
    """Map search results to public source references."""
    sources: list[AnswerSource] = []
    for idx, r in enumerate(results, start=1):
        sources.append(
            AnswerSource(
                source_index=idx,
                material_id=r.metadata.material_id or r.material_id,
                course_id=r.metadata.course_id or r.course_id,
                material_title=r.metadata.material_title,
                original_filename=r.metadata.original_filename,
                source_location=r.metadata.source_location,
                score=r.score,
            )
        )
    return sources


_EMPTY_QUERY_ANSWER = (
    "Please type a question and I'll do my best to help."
)

_FALLBACK_ANSWER = (
    "I couldn't produce a clear answer to that right now. "
    "Please try rephrasing your question."
)

# Number of chunks retrieved by default for a normal question-answer turn.
# Measured in the live diagnostic against the real indexed PDF: the 3-chunk
# prompt is ~1700 tokens and, with the GPU warm, the full RAG generation
# completes in ~2-3s. The 3 chunks are also grounding-relevant: at top_k=2 a
# broad question like "what areas does financial management cover?" retrieved
# only two narrow chunks and gave a partly over-general answer, while top_k=3
# answered it squarely from the material. The latency risk under GPU-memory
# pressure comes from unbounded generation plus a huge prompt, so keep retrieval
# small but meaningful and cap generation length separately.
DEFAULT_ANSWER_TOP_K = 3

# Maximum generated tokens for a normal chat answer. A concise grounded
# answer to a study question typically finishes in a few dozen tokens, so this
# is a budget ceiling, not a target. It replaces the old hardcoded 1024 so a
# local model can never ramble for minutes (which, under CPU-fallback resource
# pressure, is the main source of the end-to-end timeouts). Summary generation
# overrides this with its own larger budget.
DEFAULT_ANSWER_MAX_TOKENS = 512


def _retrieval_query(query: str, history: list[ConversationTurn]) -> str:
    """Build the text used for vector search.

    A follow-up such as "give me another example" carries almost no searchable
    terms on its own, so the previous user turn is prepended to keep retrieval
    pointed at the same topic. Without history the query is used unchanged.
    """
    if not history:
        return query
    for turn in reversed(history):
        if turn.role == "user" and turn.content.strip():
            return f"{turn.content.strip()}\n{query}"
    return query


def answer_question(
    knowledge_base: KnowledgeBase,
    llm: LLMProvider,
    *,
    query: str,
    user_id: str,
    course_id: str | None = None,
    material_id: str | None = None,
    top_k: int = DEFAULT_ANSWER_TOP_K,
    max_tokens: int = DEFAULT_ANSWER_MAX_TOKENS,
    history: list[ConversationTurn] | None = None,
) -> AnswerResult:
    """Answer a question using the user's material as extra context.

    The model always answers: retrieved chunks are supplied as supplementary
    context when the search finds something relevant, and the question is
    still answered from the model's own knowledge when it does not.

    Parameters
    ----------
    knowledge_base:
        The Phase 2 searchable index.
    llm:
        The LLM provider for text generation.
    query:
        The student's question.
    user_id:
        **Authenticated** user id (never taken from the client).
    course_id:
        Optional course scope (must belong to the user).
    material_id:
        Optional material scope (must belong to the user).
    top_k:
        Number of chunks to retrieve (default ``DEFAULT_ANSWER_TOP_K = 3``).
    max_tokens:
        Maximum number of tokens the model may generate for this answer
        (default ``DEFAULT_ANSWER_MAX_TOKENS = 512``), passed through to the
        provider instead of being hardcoded at the call site.
    history:
        Optional earlier turns, so follow-up questions are answered in the
        context of the conversation.

    Returns
    -------
    AnswerResult
        The answer with any source references that were used as context.
    """
    if not query or not query.strip():
        return AnswerResult(
            answer=_EMPTY_QUERY_ANSWER,
            sources=[],
            has_context=False,
        )

    turns = list(history or [])

    results = knowledge_base.search(
        _retrieval_query(query.strip(), turns),
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        top_k=top_k,
    )

    sources = sources_from_results(results)

    system_prompt, user_prompt = build_grounded_prompt(query, results, turns)

    try:
        response: LLMResponse = llm.generate(
            user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=max_tokens,
        )
    except Exception:
        return AnswerResult(
            answer=(
                "The language model is temporarily unavailable. "
                "Please try again later."
            ),
            sources=sources,
            has_context=bool(results),
            model="",
        )

    answer = strip_thinking_sections(response.text).strip()
    if not answer:
        answer = _FALLBACK_ANSWER

    return AnswerResult(
        answer=answer,
        sources=sources,
        has_context=bool(results),
        model=response.model,
    )
