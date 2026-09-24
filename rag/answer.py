"""RAG answer service: orchestrates search -> context -> LLM -> grounded answer.

This module ties together the Phase 2 knowledge base search with the Phase 3
LLM provider through the context builder.  It enforces:

- **Ownership**: search is always scoped to the authenticated user.
- **Grounding**: the LLM prompt forces answers from retrieved material only.
- **No-context behaviour**: when no material matches, a safe fallback is returned.
- **Prompt-injection defence**: retrieved text is wrapped as data, not instructions.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from rag.context_builder import (
    NO_CONTEXT_SYSTEM_PROMPT,
    build_grounded_prompt,
)
from rag.conversation import (
    RESOLUTION_CONFIDENCE_THRESHOLD,
    ConversationTurn,
    resolve_query,
)
from rag.evidence import collect_evidence, collect_visual_evidence
from rag.intent import (
    QueryIntent,
    RELIABLE_CONFIDENCE_THRESHOLD,
    analyze_query,
)
from rag.knowledge_base import KnowledgeBase
from rag.llm.base import LLMProvider, LLMResponse
from rag.llm.cleanup import strip_thinking_sections
from rag.models import SearchResult, VisualElement


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
    """Complete answer returned by the RAG engine.

    ``resolved_query`` is the follow-up query after conversation/reference
    resolution (equal to the original query for standalone turns and for
    unresolved references). It is metadata for callers that persist
    conversation state; it never grants the previous answer any authority.
    """

    answer: str
    sources: list[AnswerSource] = field(default_factory=list)
    has_context: bool = True
    model: str = ""
    resolved_query: str | None = None


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


def sources_from_visuals(
    visuals: list[VisualElement] | tuple[VisualElement, ...],
    *,
    start_index: int = 1,
) -> list[AnswerSource]:
    """Map visual elements to public source references after the text sources.

    ``start_index`` is ``len(sources_from_results(results)) + 1`` so numbering
    continues seamlessly and matches the prompt's ``VISUAL SOURCE [Source N]``
    blocks. Visual sources carry no similarity score; they are chosen by
    keyword match instead.
    """
    sources: list[AnswerSource] = []
    for idx, visual in enumerate(visuals, start=start_index):
        sources.append(
            AnswerSource(
                source_index=idx,
                material_id=visual.material_id or "",
                course_id=visual.course_id or "",
                material_title=visual.material_title,
                original_filename=visual.original_filename,
                source_location=visual.source_location,
            )
        )
    return sources


_NO_CONTEXT_ANSWER = (
    "I don't have enough information in your study materials to answer "
    "that question. Please upload relevant documents or try rephrasing."
)

_FALLBACK_ANSWER = (
    "I couldn't produce a clear answer from the retrieved material right "
    "now. Please try rephrasing your question."
)

# Number of evidence chunks used per normal question-answer turn. Retrieval
# scores a slightly larger candidate pool (see :mod:`rag.evidence`) and narrows
# it down to this many chunks, so this value bounds both the prompt size and
# the source list. Measured in the live diagnostic against the real indexed
# PDF: the 3-chunk prompt is ~1700 tokens and, with the GPU warm, the full RAG
# generation completes in ~2-3s. The 3 chunks are also grounding-relevant: at
# top_k=2 a broad question like "what areas does financial management cover?"
# retrieved only two narrow chunks and gave a partly over-general answer, while
# top_k=3 answered it squarely from the material. The latency risk under
# GPU-memory pressure comes from unbounded generation plus a huge prompt, so
# keep retrieval small but meaningful and cap generation length separately.
DEFAULT_ANSWER_TOP_K = 3

# Maximum number of visual elements attached to one visual answer. Visual
# evidence is supplementary metadata for figures/diagrams/charts, so two well
# matched visuals are enough to answer "which diagram" / "explain this
# figure" style questions without bloating the prompt.
DEFAULT_VISUAL_TOP_K = 2

# Maximum generated tokens for a normal chat answer. A concise grounded
# answer to a study question typically finishes in a few dozen tokens, so this
# is a budget ceiling, not a target. It replaces the old hardcoded 1024 so a
# local model can never ramble for minutes (which, under CPU-fallback resource
# pressure, is the main source of the end-to-end timeouts). Summary generation
# overrides this with its own larger budget.
DEFAULT_ANSWER_MAX_TOKENS = 512


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
    history: Sequence[ConversationTurn] = (),
) -> AnswerResult:
    """Answer a question grounded in the user's indexed study materials.

    Pipeline order (Phase 3 conversation support):

        raw user message
        -> conversation/reference resolution
        -> resolved query
        -> Phase 1 typo + intent analysis
        -> Phase 2 multi-source RAG evidence
        -> grounded LLM transformation
        -> answer + sources

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
        Maximum number of evidence chunks to use in the answer (default
        ``DEFAULT_ANSWER_TOP_K = 3``). Evidence may combine chunks from
        several materials (see :mod:`rag.evidence`).
    max_tokens:
        Maximum number of tokens the model may generate for this answer
        (default ``DEFAULT_ANSWER_MAX_TOKENS = 512``), passed through to the
        provider instead of being hardcoded at the call site.
    history:
        Recent :class:`ConversationTurn` records used ONLY to resolve
        references in ``query`` (e.g. "compare it with UDP"). History never
        becomes RAG evidence: retrieval always runs fresh against the resolved
        query and previous assistant answers are never placed in the
        grounded prompt.

    Returns
    -------
    AnswerResult
        The grounded answer with source references.
    """
    if not query or not query.strip():
        return AnswerResult(
            answer=_NO_CONTEXT_ANSWER,
            sources=[],
            has_context=False,
        )

    query_text = query.strip()

    # Conversation/reference resolution happens BEFORE Phase 1, so a follow-up
    # becomes a standalone question that the existing typo + intent analysis
    # and fresh RAG retrieval can handle. History only supplies the topic that
    # the user's own previous message already named; it never adds facts.
    resolved_query: str | None = None
    if history:
        resolution = resolve_query(query_text, list(history))
        if (
            resolution.was_resolved
            and resolution.confidence >= RESOLUTION_CONFIDENCE_THRESHOLD
        ):
            resolved_query = resolution.resolved_query.strip()
            query_text = resolved_query

    intent: QueryIntent = analyze_query(query_text)
    reliable_intent = intent.confidence >= RELIABLE_CONFIDENCE_THRESHOLD

    # The corrected query is used for retrieval: typo tolerance exists
    # specifically to make KnowledgeBase search find the right material.
    # When the analysis is unreliable the original wording is preserved.
    retrieval_query = intent.corrected_query.strip() if reliable_intent else query_text

    results = collect_evidence(
        knowledge_base,
        query=retrieval_query,
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        max_evidence=top_k,
    )

    # Visual evidence is only fetched for visual queries; regular text
    # questions never pull visuals into the prompt. Best-effort and silent:
    # a store without visual support simply contributes no visual sources.
    visuals: list[VisualElement] = []
    if intent.is_visual:
        visuals = collect_visual_evidence(
            knowledge_base,
            query=retrieval_query,
            user_id=user_id,
            course_id=course_id,
            material_id=material_id,
            max_visuals=DEFAULT_VISUAL_TOP_K,
        )

    sources = sources_from_results(results)
    visual_sources = sources_from_visuals(
        visuals, start_index=len(sources) + 1
    )
    all_sources = sources + visual_sources

    if not results and not visuals:
        return AnswerResult(
            answer=_NO_CONTEXT_ANSWER,
            sources=[],
            has_context=False,
            resolved_query=resolved_query,
        )

    system_prompt, user_prompt = build_grounded_prompt(
        retrieval_query,
        results,
        intent=intent if reliable_intent else None,
        visuals=visuals,
    )

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
            sources=all_sources,
            has_context=True,
            model="",
            resolved_query=resolved_query,
        )

    answer = strip_thinking_sections(response.text).strip()
    if not answer:
        answer = _FALLBACK_ANSWER

    return AnswerResult(
        answer=answer,
        sources=all_sources,
        has_context=True,
        model=response.model,
        resolved_query=resolved_query,
    )
