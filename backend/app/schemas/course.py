import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class TeacherSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    email: str


class CourseCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    code: str = Field(min_length=1, max_length=50)
    description: str | None = None


class CourseResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    code: str
    description: str | None
    teacher_id: uuid.UUID | None
    teacher: TeacherSummary | None
    created_at: datetime