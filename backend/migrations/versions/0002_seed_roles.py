"""seed standard roles

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-05

NOTE: Fill in `down_revision` with the actual revision ID produced by
the 0001_initial_schema autogenerate migration before applying.
"""

from __future__ import annotations

import uuid

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "04dd1eabaa39"
branch_labels: str | tuple[str, ...] | None = None
depends_on: str | tuple[str, ...] | None = None

_ROLES = [
    ("user", 1),
    ("surveyor", 2),
    ("blaster", 3),
    ("admin", 4),
]


def upgrade() -> None:
    conn = op.get_bind()
    for name, level in _ROLES:
        conn.execute(
            sa.text(
                "INSERT INTO role (id, name, level) VALUES (:id, :name, :level)"
                " ON CONFLICT (name) DO NOTHING"
            ),
            {"id": str(uuid.uuid4()), "name": name, "level": level},
        )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM role WHERE name IN ('user', 'surveyor', 'blaster', 'admin')")
    )
