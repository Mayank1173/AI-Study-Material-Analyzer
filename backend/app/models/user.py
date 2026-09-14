import uuid
from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, String, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

VALID_USER_ROLES = ("student", "teacher")


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        CheckConstraint(
            "role IN ('student', 'teacher')", name="role"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False, unique=True)
    password_hash: Mapped[str | None] = mapped_column(
        String(255), nullable=True
    )
    role: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        server_default="student",
        default="student",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    study_materials: Mapped[list["StudyMaterial"]] = relationship(
        back_populates="uploader"
    )
    courses_owned: Mapped[list["Course"]] = relationship(
        back_populates="teacher"
    )
    course_enrollments: Mapped[list["CourseEnrollment"]] = relationship(
        back_populates="student"
    )