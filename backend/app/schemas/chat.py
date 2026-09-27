"""Pydantic schemas for the /api/chat endpoints."""

from __future__ import annotations

import uuid

from pydantic import BaseModel, Field


class ChatTurn(BaseModel):
    """One earlier chat turn, supplied so follow-up questions keep context."""

    role: str = Field(pattern="^(user|assistant)$")
    content: str = Field(min_length=1, max_length=4000)


class ChatRequest(BaseModel):
    """Inbound chat message from the frontend."""

    message: str = Field(min_length=1, max_length=4000)
    course_id: str | None = Field(default=None, max_length=64)
    material_id: str | None = Field(default=None, max_length=64)
    history: list[ChatTurn] = Field(default_factory=list, max_length=20)


class ChatSource(BaseModel):
    """One source reference attached to the answer."""

    source_index: int
    material_id: str
    course_id: str
    material_title: str | None = None
    original_filename: str | None = None
    source_location: str | None = None
    score: float = 0.0


class ChatResponse(BaseModel):
    """Structured answer returned to the frontend."""

    answer: str
    sources: list[ChatSource] = []
    has_context: bool = True


class SummaryRequest(BaseModel):
    """Request to generate an AI study summary for a subject.

    The authenticated user's id always comes from the JWT, never from this
    body. ``course_id`` optionally scopes retrieval to one subject; it can only
    narrow the user's own index.
    """

    course_id: uuid.UUID | None = Field(
        default=None,
        description="Optional subject (course) to scope the summary to",
    )


class SummaryResponse(BaseModel):
    """Grounded study summary returned to the frontend."""

    summary: str
    sources: list[ChatSource] = []
    has_context: bool = True
