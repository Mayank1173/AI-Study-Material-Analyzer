"""study_materials: add file management metadata columns

Revision ID: 0002_file_metadata
Revises: 0001_initial_schema
Create Date: 2026-09-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_file_metadata"
down_revision: Union[str, Sequence[str], None] = "0001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "study_materials", sa.Column("file_size", sa.BigInteger(), nullable=True)
    )
    op.add_column(
        "study_materials", sa.Column("mime_type", sa.String(length=255), nullable=True)
    )
    op.add_column(
        "study_materials",
        sa.Column("stored_file_name", sa.String(length=255), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("study_materials", "stored_file_name")
    op.drop_column("study_materials", "mime_type")
    op.drop_column("study_materials", "file_size")