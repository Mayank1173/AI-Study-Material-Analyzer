"""users: add password_hash and role columns

Revision ID: 0003_add_user_auth_fields
Revises: 0002_file_metadata
Create Date: 2026-09-13

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003_add_user_auth_fields"
down_revision: Union[str, Sequence[str], None] = "0002_file_metadata"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("password_hash", sa.String(length=255), nullable=True),
    )
    op.add_column(
        "users",
        sa.Column(
            "role",
            sa.String(length=20),
            server_default="student",
            nullable=False,
        ),
    )
    op.create_check_constraint(
        "role",
        "users",
        "role IN ('student', 'teacher')",
    )


def downgrade() -> None:
    op.drop_constraint("role", "users", type_="check")
    op.drop_column("users", "role")
    op.drop_column("users", "password_hash")