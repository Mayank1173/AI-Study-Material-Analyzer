from __future__ import annotations

import uuid
from typing import Any

from pydantic import BaseModel, Field, field_validator


class PyqQuestion(BaseModel):
    question: str
    years_appeared: list[str] | str = Field(default="")
    unit: str | None = None
    marks: int | str | None = None
    importance: str = Field(default="Medium")
    frequency: int = Field(default=0)
    files: list[str] = Field(default_factory=list)
    answer: str | None = None


class PyqAnalysisRequest(BaseModel):
    course_id: str | None = Field(default=None)
    num_questions: int = Field(default=10, ge=1, le=50)
    answer_length: str = Field(default="Medium")
    selected_marks: str | None = Field(default=None)
    file_ids: list[str] | None = Field(default=None)


class PyqAnalysisResponse(BaseModel):
    questions: list[PyqQuestion] = Field(default_factory=list)
    total_questions: int = 0
    repeated: int = 0
    top_priority: int = 0
    summary: dict[str, Any] = Field(default_factory=dict)
    analyzed_files: list[str] = Field(
        default_factory=list,
        description="Files that were read successfully",
    )
    failed_files: list[str] = Field(
        default_factory=list,
        description=(
            "Files that could not be read or owned by another user. Lets the "
            "frontend distinguish an extraction failure from an empty result."
        ),
    )


class PyqAnswerStyle(BaseModel):
    """Selected answer-style options for a generated answer."""

    point_wise: bool = Field(default=False)
    paragraph_format: bool = Field(default=False)
    include_diagrams: bool = Field(default=False)
    include_examples: bool = Field(default=False)
    simple_language: bool = Field(default=False)
    step_by_step: bool = Field(default=False)
    include_definitions: bool = Field(default=False)
    pros_and_cons: bool = Field(default=False)


class PyqAnswerRequest(BaseModel):
    """Generate an exam answer for one previous-year question.

    The authenticated user's id always comes from the JWT, never from this
    body. ``course_id`` optionally scopes retrieval to one course; it can only
    narrow the user's own index.
    """

    question: str = Field(min_length=1, max_length=4000)
    course_id: uuid.UUID | None = Field(
        default=None,
        description="Optional course to scope study-material retrieval to",
    )
    course_name: str | None = Field(
        default=None,
        max_length=255,
        description="Human-readable course label used for terminology only",
    )
    marks: int | None = Field(
        default=None,
        ge=1,
        le=100,
        description="Marks the question carried in the paper",
    )
    answer_format: str | None = Field(
        default=None,
        max_length=32,
        description="Short | Medium | Detailed | Exam-Oriented",
    )
    styles: PyqAnswerStyle | None = None

    @field_validator("question")
    @classmethod
    def _question_not_blank(cls, value: str) -> str:
        """Reject whitespace-only questions: min_length alone allows them."""
        stripped = value.strip()
        if not stripped:
            raise ValueError("question must not be blank")
        return stripped


class PyqAnswerSource(BaseModel):
    """One source reference used to ground a generated answer."""

    source_index: int
    material_id: str
    course_id: str
    material_title: str | None = None
    original_filename: str | None = None
    source_location: str | None = None
    score: float = 0.0


class PyqAnswerResponse(BaseModel):
    """A generated exam answer plus its provenance.

    ``has_context`` is the grounding signal: ``False`` means no sufficiently
    relevant study material was found and the answer comes from the model's
    general knowledge. The frontend must surface that to the user rather than
    implying the answer came from uploaded material.
    """

    answer: str
    has_context: bool = False
    sources: list[PyqAnswerSource] = Field(default_factory=list)
    model: str = ""
    marks: int | None = None
    answer_format: str | None = None
    course_name: str | None = None
