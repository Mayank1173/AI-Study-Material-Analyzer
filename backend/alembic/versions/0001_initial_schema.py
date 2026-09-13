"""initial schema: users, courses, study_materials

Revision ID: 0001_initial_schema
Revises:
Create Date: 2026-09-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001_initial_schema"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_users")),
        sa.UniqueConstraint("email", name=op.f("uq_users_email")),
    )

    op.create_table(
        "courses",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("code", sa.String(length=50), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_courses")),
        sa.UniqueConstraint("code", name=op.f("uq_courses_code")),
    )
    op.create_index("ix_courses_name", "courses", ["name"], unique=False)

    op.create_table(
        "study_materials",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("course_id", sa.Uuid(), nullable=False),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("material_type", sa.String(length=50), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=True),
        sa.Column("file_path", sa.String(length=1024), nullable=True),
        sa.Column("source_url", sa.String(length=2048), nullable=True),
        sa.Column(
            "status",
            sa.String(length=50),
            server_default="uploaded",
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["course_id"],
            ["courses.id"],
            name=op.f("fk_study_materials_courses_course_id"),
        ),
        sa.ForeignKeyConstraint(
            ["uploaded_by"],
            ["users.id"],
            name=op.f("fk_study_materials_users_uploaded_by"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_study_materials")),
    )
    op.create_index(
        "ix_study_materials_course_id", "study_materials", ["course_id"], unique=False
    )
    op.create_index(
        "ix_study_materials_uploaded_by",
        "study_materials",
        ["uploaded_by"],
        unique=False,
    )
    op.create_index(
        "ix_study_materials_material_type",
        "study_materials",
        ["material_type"],
        unique=False,
    )
    op.create_index(
        "ix_study_materials_status", "study_materials", ["status"], unique=False
    )


def downgrade() -> None:
    op.drop_index("ix_study_materials_uploaded_by", table_name="study_materials")
    op.drop_index("ix_study_materials_status", table_name="study_materials")
    op.drop_index("ix_study_materials_material_type", table_name="study_materials")
    op.drop_index("ix_study_materials_course_id", table_name="study_materials")
    op.drop_table("study_materials")
    op.drop_index("ix_courses_name", table_name="courses")
    op.drop_table("courses")
    op.drop_table("users")