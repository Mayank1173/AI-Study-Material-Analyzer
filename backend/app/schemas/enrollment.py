import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class EnrollmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    student_id: uuid.UUID
    enrolled_at: datetime


class EnrolledStudentResponse(BaseModel):
    id: uuid.UUID
    name: str
    email: str
    enrolled_at: datetime


class EnrollmentStatusResponse(BaseModel):
    course_id: uuid.UUID
    is_enrolled: bool
    enrolled_at: datetime | None = None