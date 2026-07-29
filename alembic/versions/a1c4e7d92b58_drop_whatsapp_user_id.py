"""drop whatsapp_user_id from proposals

Vestigial from a WhatsApp-first design. Every row carried the hardcoded literal
"web", which made two things dead weight:

  - idx_proposals_user indexed a single-valued column. Zero selectivity, so the
    planner could never use it, but it still cost a write on every insert.
  - get_pending_proposal_for_user() filtered on it and had no callers. Tenant
    isolation is enforced by TenantSession, not by this column.

Revision ID: a1c4e7d92b58
Revises: 3fb9b15cffbb
Create Date: 2026-07-29
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "a1c4e7d92b58"
down_revision: str | None = "3fb9b15cffbb"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_index("idx_proposals_user", table_name="proposals")
    op.drop_column("proposals", "whatsapp_user_id")


def downgrade() -> None:
    # Three steps, not one: the column was NOT NULL with no server default, so
    # adding it back directly fails on any table that already has rows. Add it
    # nullable, backfill the literal the application used to write, then apply
    # the constraint.
    op.add_column(
        "proposals",
        sa.Column("whatsapp_user_id", sa.String(length=100), nullable=True),
    )
    op.execute("UPDATE proposals SET whatsapp_user_id = 'web' WHERE whatsapp_user_id IS NULL")
    op.alter_column("proposals", "whatsapp_user_id", nullable=False)
    op.create_index("idx_proposals_user", "proposals", ["whatsapp_user_id"], unique=False)
