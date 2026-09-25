"""Chat endpoints: /api/chat and /api/chat/summary.

JWT-authenticated.  The authenticated user's id is the sole authority for
scoping the knowledge-base search -- never taken from the request body.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_active_user
from app.core.config import get_settings
from app.db.session import get_db
from app.models import Course, User
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    ChatSource,
    SummaryRequest,
    SummaryResponse,
)
from rag.answer import AnswerResult, answer_question
from rag.knowledge_base import KnowledgeBase, get_knowledge_base
from rag.llm import LLMProvider, MockProvider, OllamaProvider
from rag.summary import generate_study_summary

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["Chat"])


def get_llm_provider() -> LLMProvider:
    """Build an LLM provider from the current backend settings.

    ``LLM_PROVIDER`` selects the backend: ``"ollama"`` (default) or ``"mock"``.
    ``LLM_MODEL`` and ``OLLAMA_BASE_URL`` configure the chosen provider.
    In tests this is overridden via ``dependency_overrides``.
    """
    settings = get_settings()
    provider_name = settings.llm_provider.lower()

    if provider_name == "mock":
        return MockProvider()

    return OllamaProvider(
        model=settings.llm_model,
        base_url=settings.ollama_base_url,
        timeout=settings.llm_timeout_seconds,
        think=settings.llm_think,
    )


def _get_kb() -> Iterable[KnowledgeBase]:
    """Yield a KnowledgeBase for the request, closing it afterwards.

    In tests this is overridden via ``dependency_overrides`` to use a
    temporary vector store.
    """
    try:
        kb = get_knowledge_base()
    except Exception:
        logger.exception("Failed to open knowledge base")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Knowledge base is temporarily unavailable",
        )
    try:
        yield kb
    finally:
        kb.close()


def _to_chat_source(src) -> ChatSource:
    return ChatSource(
        source_index=src.source_index,
        material_id=src.material_id,
        course_id=src.course_id,
        material_title=src.material_title,
        original_filename=src.original_filename,
        source_location=src.source_location,
        score=src.score,
    )


@router.post("", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    current_user: User = Depends(get_current_active_user),
    kb: KnowledgeBase = Depends(_get_kb),
    llm: LLMProvider = Depends(get_llm_provider),
) -> ChatResponse:
    """Answer a question using the user's indexed study materials.

    Security:
    - Authentication is required (JWT Bearer token).
    - ``user_id`` is taken from the JWT, never from the request body.
    - KnowledgeBase.search receives the authenticated user's id, enforcing
      multi-tenant isolation.
    """
    user_id = str(current_user.id)

    try:
        settings = get_settings()
        result: AnswerResult = answer_question(
            kb,
            llm,
            query=body.message,
            user_id=user_id,
            course_id=body.course_id,
            material_id=body.material_id,
            max_tokens=settings.llm_max_tokens,
        )
    except Exception:
        logger.exception("RAG answer_question failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate an answer. Please try again later.",
        )

    return ChatResponse(
        answer=result.answer,
        sources=[_to_chat_source(s) for s in result.sources],
        has_context=result.has_context,
    )


@router.post("/summary", response_model=SummaryResponse)
def study_summary(
    body: SummaryRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    kb: KnowledgeBase = Depends(_get_kb),
    llm: LLMProvider = Depends(get_llm_provider),
) -> SummaryResponse:
    """Generate an AI study summary grounded in the user's indexed material.

    Security (mirrors /api/chat):
    - Authentication is required (JWT Bearer token).
    - ``user_id`` is taken from the JWT, never from the request body.
    - KnowledgeBase.search receives the authenticated user's id, enforcing
      multi-tenant isolation; ``course_id`` only narrows the user's own index.
    """
    user_id = str(current_user.id)

    subject_name: str | None = None
    if body.course_id is not None:
        course = db.get(Course, body.course_id)
        if course is not None:
            subject_name = course.name

    try:
        result = generate_study_summary(
            kb,
            llm,
            user_id=user_id,
            course_id=str(body.course_id) if body.course_id is not None else None,
            subject_name=subject_name,
        )
    except Exception:
        logger.exception("RAG generate_study_summary failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate the study summary. Please try again later.",
        )

    return SummaryResponse(
        summary=result.summary,
        sources=[_to_chat_source(s) for s in result.sources],
        has_context=result.has_context,
    )
