"""add course ownership and student enrollment

Revision ID: 0004_course_ownership_and_enrollments
Revises: 0003_add_user_auth_fields
Create Date: 2026-09-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_course_ownership_and_enrollments"
down_revision: Union[str, Sequence[str], None] = "0003_add_user_auth_fields"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # courses.teacher_id is added as nullable on purpose: existing databases
    # may contain courses created before teacher ownership existed, and this
    # migration must not destroy that data. NOT NULL is enforced for all newly
    # created courses by the application layer (the API only accepts course
    # creation from an authenticated teacher).
    op.add_column(
        "courses", sa.Column("teacher_id", sa.Uuid(), nullable=True)
    )
    op.create_foreign_key(
        "fk_courses_users_teacher_id",
        "courses",
        "users",
        ["teacher_id"],
        ["id"],
    )
    op.create_index(
        "ix_courses_teacher_id", "courses", ["teacher_id"], unique=False
    )

    op.create_table(
        "course_enrollments",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("student_id", sa.Uuid(), nullable=False),
        sa.Column(
            "enrolled_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_course_enrollments_courses_course_id"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["student_id"],
            ["users.id"],
            name=op.f("fk_course_enrollments_users_student_id"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_course_enrollments")),
        sa.UniqueConstraint(
            "course_id",
            "student_id",
            name=op.f("uq_course_enrollments_course_id_student_id"),
        ),
    )
    op.create_index(
        "ix_course_enrollments_course_id",
        "course_enrollments",
        ["course_id"],
        unique=False,
    )
    op.create_index(
        "ix_course_enrollments_student_id",
        "course_enrollments",
        ["student_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_course_enrollments_student_id", table_name="course_enrollments"
    )
    op.drop_index(
        "ix_course_enrollments_course_id", table_name="course_enrollments"
    )
    op.drop_table("course_enrollments")
    op.drop_index("ix_courses_teacher_id", table_name="courses")
    op.drop_constraint(
        "fk_courses_users_teacher_id", "courses", type_="foreignkey"
    )
    op.drop_column("courses", "teacher_id")