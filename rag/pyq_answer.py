"""RAG exam-answer service for previous-year questions (PYQs).

This module composes the same building blocks as :mod:`rag.answer` and
:mod:`rag.summary` (owner-scoped search -> context builder -> LLM provider)
to answer a single previous-year question in the exam slot it was asked in.
It deliberately does not create a second retrieval stack: it reuses
:class:`rag.knowledge_base.KnowledgeBase` for embedding search and the shared
vector store, :mod:`rag.context_builder` for prompt construction (including the
same prompt-injection delimiters), and the caller's existing
:class:`rag.llm.base.LLMProvider`.

Behaviour it adds on top of the chat engine:

- **Grounding decision**: retrieval is filtered by a minimum cosine relevance
  score, so "some chunk was returned" is not mistaken for "the material covers
  this question". ``has_context`` reports that decision so the caller can tell
  the user when an answer came from general knowledge instead.
- **Exam-slot shaping**: the requested marks and answer format drive both the
  prompt (via ``build_exam_directive``) and the generation token budget.
- **Honest provenance**: the result carries ``has_context`` so the UI never
  presents a general-knowledge answer as if it came from uploaded material.
- **Honest failure**: when the provider cannot produce text, this raises
  :class:`PyqAnswerGenerationError` instead of returning a result whose
  ``answer`` holds an error string. A failed generation is never reported as a
  successful answer.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from rag.answer import AnswerSource, sources_from_results
from rag.context_builder import build_exam_answer_prompt
from rag.knowledge_base import KnowledgeBase
from rag.llm.base import (
    LLMError,
    LLMProvider,
    LLMRequestError,
    LLMResponse,
    LLMTimeoutError,
)
from rag.llm.cleanup import strip_thinking_sections
from rag.models import SearchResult

logger = logging.getLogger(__name__)

# Retrieval breadth for a single exam answer. Kept small like the chat engine:
# a model answer is grounded in a focused amount of material, and a large
# prompt is the main driver of end-to-end latency under resource pressure.
DEFAULT_PYQ_ANSWER_TOP_K = 4

# Minimum cosine similarity for a chunk to count as relevant support. Cosine
# similarity between unrelated sentence pairs on a typical sentence-transformer
# backend sits well below this, so it filters noise while keeping genuine
# paraphrase matches (which is what repeated PYQs are).
DEFAULT_MIN_RELEVANCE_SCORE = 0.35

# Generation budgets by requested marks. These are ceilings, not targets: a
# 2-mark answer finishes in a few dozen tokens, a 20-mark answer needs real
# room for structure and multiple parts.
_MARKS_TOKEN_BUDGETS = (
    (20, 1600),
    (10, 1100),
    (5, 700),
    (2, 350),
)

# Budget used when marks are unknown or out of the expected set.
DEFAULT_ANSWER_MAX_TOKENS = 700

# Cap even a 20-mark answer, so a local model can never run unbounded.
MAX_ANSWER_MAX_TOKENS = 2048

_EMPTY_ANSWER = (
    "An answer could not be generated for this question. Please try again."
)


class PyqAnswerGenerationError(LLMError):
    """Answer generation failed; no answer was produced.

    Raised instead of returning a :class:`PyqAnswerResult` whose ``answer``
    holds an error string. Returning a failed generation as a normal result
    makes the API answer ``200 OK`` and lets the UI render an error message
    inside the answer box as though the model had produced it.

    Attributes
    ----------
    timed_out:
        ``True`` when the provider reported a timeout, which is a latency
        problem rather than an outage.
    """

    def __init__(self, message: str, *, timed_out: bool = False) -> None:
        super().__init__(message)
        self.timed_out = timed_out


@dataclass(frozen=True)
class PyqAnswerResult:
    """A generated exam answer plus its provenance.

    ``has_context`` is the grounding signal: ``True`` means the answer was
    grounded in retrieved study material, ``False`` means it was generated
    from the model's general knowledge because no sufficiently relevant
    material was found. ``sources`` is empty in the fallback case.
    """

    answer: str
    has_context: bool = False
    sources: list[AnswerSource] = field(default_factory=list)
    model: str = ""
    marks: int | None = None
    answer_format: str | None = None
    course_name: str | None = None


def max_tokens_for_marks(marks: int | None) -> int:
    """Generation budget for an answer to a question worth ``marks``."""
    if not marks or marks <= 0:
        return DEFAULT_ANSWER_MAX_TOKENS
    for threshold, budget in _MARKS_TOKEN_BUDGETS:
        if marks >= threshold:
            return min(budget, MAX_ANSWER_MAX_TOKENS)
    return min(marks * 90, MAX_ANSWER_MAX_TOKENS)


def relevant_results(
    results: list[SearchResult],
    min_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
) -> list[SearchResult]:
    """Keep only chunks whose similarity clears the relevance threshold.

    Search always returns its nearest neighbours, so an empty or weak result
    set is common even when the index holds good material for other topics.
    Filtering here is what makes "no relevant context" a real decision rather
    than an artefact of ``top_k``.
    """
    return [r for r in results if r.score >= min_score]


def answer_pyq_question(
    knowledge_base: KnowledgeBase,
    llm: LLMProvider,
    *,
    question: str,
    user_id: str,
    course_id: str | None = None,
    course_name: str | None = None,
    marks: int | None = None,
    answer_format: str | None = None,
    styles: dict[str, bool] | None = None,
    top_k: int = DEFAULT_PYQ_ANSWER_TOP_K,
    min_relevance_score: float = DEFAULT_MIN_RELEVANCE_SCORE,
) -> PyqAnswerResult:
    """Answer one previous-year question in its exam slot.

    Retrieval is scoped to ``user_id`` (the authenticated owner); ``course_id``
    can only narrow that set. When no chunk clears ``min_relevance_score`` the
    question is still answered, from the model's general knowledge, and the
    result is flagged ``has_context=False`` so the caller can say so.

    Parameters
    ----------
    knowledge_base:
        The existing Phase 2 searchable index (embeddings + vector store).
    llm:
        The existing LLM provider used by chat and summaries.
    question:
        The previous-year question text.
    user_id:
        **Authenticated** user id (never taken from the client).
    course_id:
        Optional course scope; must belong to the user.
    course_name:
        Optional human-readable course label, used only to keep terminology
        and scope consistent. Never a source of facts.
    marks:
        Marks the question carried in the paper; drives length and budget.
    answer_format:
        Selected answer format (``Short``/``Medium``/``Detailed``/
        ``Exam-Oriented``); drives structure.
    styles:
        Selected answer-style options (point-wise, diagrams, examples, ...).
    top_k:
        Number of chunks to retrieve before relevance filtering.
    min_relevance_score:
        Minimum cosine similarity for a chunk to count as relevant support.

    Returns
    -------
    PyqAnswerResult
        The answer, its sources, and whether it was material-grounded.

    Raises
    ------
    PyqAnswerGenerationError
        If the LLM provider fails or returns no text. ``timed_out`` is ``True``
        when the provider reported a timeout, letting the caller distinguish a
        slow model from an unreachable backend.
    """
    if not question or not question.strip():
        return PyqAnswerResult(
            answer=_EMPTY_ANSWER,
            has_context=False,
            sources=[],
            model="",
            marks=marks,
            answer_format=answer_format,
            course_name=course_name,
        )

    retrieved = knowledge_base.search(
        question.strip(),
        user_id=user_id,
        course_id=course_id,
        top_k=top_k,
    )

    results = relevant_results(retrieved, min_relevance_score)
    sources = sources_from_results(results)
    has_context = bool(results)

    system_prompt, user_prompt = build_exam_answer_prompt(
        question.strip(),
        results,
        marks=marks,
        answer_format=answer_format,
        course_name=course_name,
        styles=styles,
    )

    try:
        response: LLMResponse = llm.generate(
            user_prompt,
            system_prompt=system_prompt,
            temperature=0.3,
            max_tokens=max_tokens_for_marks(marks),
        )
    except LLMTimeoutError as exc:
        # Not an outage: the model was reachable but too slow for the budget.
        logger.error(
            "PYQ answer timed out for user=%s course=%s question=%r "
            "(max_tokens=%d). Raise LLM_TIMEOUT_SECONDS or lower the budget.",
            user_id,
            course_id,
            question[:120],
            max_tokens_for_marks(marks),
        )
        raise PyqAnswerGenerationError(str(exc), timed_out=True) from exc
    except LLMError as exc:
        logger.error(
            "PYQ answer generation failed for user=%s course=%s question=%r: %s",
            user_id,
            course_id,
            question[:120],
            exc,
        )
        raise PyqAnswerGenerationError(str(exc)) from exc
    except Exception as exc:
        # A provider that raises something outside the LLMError hierarchy must
        # still not be mistaken for a successful, empty answer.
        logger.exception(
            "Unexpected error generating PYQ answer for user=%s course=%s "
            "question=%r",
            user_id,
            course_id,
            question[:120],
        )
        raise PyqAnswerGenerationError(
            "The language model failed to generate an answer."
        ) from exc

    answer = strip_thinking_sections(response.text).strip()
    if not answer:
        logger.warning(
            "PYQ answer generation produced no text for user=%s question=%r",
            user_id,
            question[:120],
        )
        raise PyqAnswerGenerationError(
            "The language model returned an empty answer."
        )

    return PyqAnswerResult(
        answer=answer,
        has_context=has_context,
        sources=sources,
        model=response.model,
        marks=marks,
        answer_format=answer_format,
        course_name=course_name,
    )