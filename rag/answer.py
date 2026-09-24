"""RAG answer service: orchestrates search -> context -> LLM -> grounded answer.

This module ties together the Phase 2 knowledge base search with the Phase 3
LLM provider through the context builder.  It enforces:

- **Ownership**: search is always scoped to the authenticated user.
- **Grounding**: the LLM prompt forces answers from retrieved material only.
- **No-context behaviour**: when no material matches, greetings still get a
  warm conversational reply via the LLM; other queries get a safe fallback.
- **Prompt-injection defence**: retrieved text is wrapped as data, not instructions.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from rag.context_builder import (
    GREETING_SYSTEM_PROMPT,
    NO_CONTEXT_SYSTEM_PROMPT,
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


_NO_CONTEXT_ANSWER = (
    "I don't have enough information in your study materials to answer "
    "that question. Please upload relevant documents or try rephrasing."
)

_FALLBACK_ANSWER = (
    "I couldn't produce a clear answer from the retrieved material right "
    "now. Please try rephrasing your question."
)

_LLM_UNAVAILABLE_ANSWER = (
    "The language model is temporarily unavailable. Please try again later."
)

# Exact casual greetings / social remarks (punctuation-stripped, lowercased).
_GREETING_EXACT = frozenset(
    {
        "hi",
        "hello",
        "hey",
        "howdy",
        "hiya",
        "yo",
        "sup",
        "thanks",
        "thank you",
        "thank you so much",
        "thanks a lot",
        "thx",
        "cheers",
        "ok",
        "okay",
        "cool",
        "great",
        "awesome",
        "nice",
        "perfect",
        "good",
        "bye",
        "goodbye",
        "see you",
        "see you later",
        "good morning",
        "good afternoon",
        "good evening",
        "good night",
        "how are you",
        "how are you doing",
        "how do you do",
        "how's it going",
        "how is it going",
        "what's up",
        "what is up",
        "how have you been",
        "long time no see",
        "hi there",
        "hey there",
        "hello there",
    }
)

_GREETING_START_RE = re.compile(
    r"^(?:hi|hello|hey|thanks|thank you|good (?:morning|afternoon|evening)|"
    r"how are you|how's it going|what's up)\b"
)


def _normalize_remark(query: str) -> str:
    text = " ".join(query.strip().lower().split())
    return text.rstrip("!.?;:,")


def _is_greeting_or_general_remark(query: str) -> bool:
    """True for casual greetings / social remarks that need no retrieval."""
    text = _normalize_remark(query)
    if not text:
        return False
    if text in _GREETING_EXACT:
        return True
    # Short openers such as "hi there how are you" or "thanks a ton".
    if len(text.split()) <= 5 and _GREETING_START_RE.match(text):
        return True
    return False

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
) -> AnswerResult:
    """Answer a question grounded in the user's indexed study materials.

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

    results = knowledge_base.search(
        query.strip(),
        user_id=user_id,
        course_id=course_id,
        material_id=material_id,
        top_k=top_k,
    )

    sources = sources_from_results(results)

    if not results:
        # Casual greetings / general remarks need no study material: route
        # them to the LLM with the no-context prompt so they get a warm,
        # conversational reply instead of a canned failure string.
        if _is_greeting_or_general_remark(query):
            try:
                response = llm.generate(
                    query.strip(),
                    system_prompt=NO_CONTEXT_SYSTEM_PROMPT,
                    temperature=0.3,
                    max_tokens=max_tokens,
                )
            except Exception:
                return AnswerResult(
                    answer=_LLM_UNAVAILABLE_ANSWER,
                    sources=[],
                    has_context=False,
                    model="",
                )
            answer = strip_thinking_sections(response.text).strip()
            if not answer:
                answer = _FALLBACK_ANSWER
            return AnswerResult(
                answer=answer,
                sources=[],
                has_context=False,
                model=response.model,
            )
        return AnswerResult(
            answer=_NO_CONTEXT_ANSWER,
            sources=[],
            has_context=False,
        )

    system_prompt, user_prompt = build_grounded_prompt(query, results)

    try:
        response: LLMResponse = llm.generate(
            user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=max_tokens,
        )
    except Exception:
        return AnswerResult(
            answer=_LLM_UNAVAILABLE_ANSWER,
            sources=sources,
            has_context=True,
            model="",
        )

    answer = strip_thinking_sections(response.text).strip()
    if not answer:
        answer = _FALLBACK_ANSWER

    return AnswerResult(
        answer=answer,
        sources=sources,
        has_context=True,
        model=response.model,
    )
