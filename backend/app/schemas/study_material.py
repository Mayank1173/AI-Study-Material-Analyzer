import uuid
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

# Status lifecycle for study materials. Processing is not implemented yet;
# uploaded -> processing -> processed/failed is reserved for a future pipeline.
VALID_MATERIAL_STATUSES = ("uploaded", "processing", "processed", "failed")
MaterialStatus = Literal["uploaded", "processing", "processed", "failed"]


class StudyMaterialCreate(BaseModel):
    course_id: uuid.UUID
    title: str = Field(min_length=1, max_length=255)
    material_type: str = Field(min_length=1, max_length=50)
    file_name: str | None = Field(default=None, max_length=255)
    file_path: str | None = Field(default=None, max_length=1024)
    source_url: str | None = Field(default=None, max_length=2048)
    status: MaterialStatus | None = None


class StudyMaterialResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    course_id: uuid.UUID
    uploaded_by: uuid.UUID
    title: str
    material_type: str
    file_name: str | None
    source_url: str | None
    file_size: int | None
    mime_type: str | None
    status: MaterialStatus
    processed_at: datetime | None
    error_message: str | None
    created_at: datetime
    updated_at: datetime