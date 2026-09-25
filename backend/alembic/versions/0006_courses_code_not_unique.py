"""drop global code uniqueness on courses

Courses now act as per-user subjects/collections: each authenticated user can
create their own subjects, so a globally unique course code is no longer
desired. Uniqueness within one owner is enforced at the application layer.

Wait: dropping the unique constraint also drops the backing unique index; no
replacement index is created because search terms are matched with ILIKE.

Revision ID: 0006_courses_code_not_unique
Revises: 0005_processing_lifecycle
Create Date: 2026-09-17

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0006_courses_code_not_unique"
down_revision: Union[str, Sequence[str], None] = "0005_processing_lifecycle"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_courses_code", "courses", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint("uq_courses_code", "courses", ["code"])