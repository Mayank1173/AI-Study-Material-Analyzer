"""study_materials: add processing lifecycle columns

Processing is not implemented yet, but the schema now carries the state a
future worker needs: when processing finished, and a safe failure message
when it could not.

Revision ID: 0005_material_processing_lifecycle
Revises: 0004_course_ownership_and_enrollments
Create Date: 2026-09-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_material_processing_lifecycle"
down_revision: Union[str, Sequence[str], None] = "0004_course_ownership_and_enrollments"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "study_materials",
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "study_materials",
        sa.Column("error_message", sa.String(length=1000), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("study_materials", "error_message")
    op.drop_column("study_materials", "processed_at")