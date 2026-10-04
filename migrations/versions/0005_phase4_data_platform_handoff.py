"""add scoped Data Agent service account

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"
DATA_AGENT_SERVICE_ACCOUNT_ID = "00000000-0000-0000-0000-000000000504"
DATA_ANALYST_ROLE_ID = "00000000-0000-0000-0000-000000000602"
WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"


def upgrade() -> None:
    op.add_column("principals", sa.Column("agent_id", sa.String(length=36), nullable=True))
    op.create_foreign_key(
        "fk_principals_agent_id",
        "principals",
        "agents",
        ["agent_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_index("ix_principals_agent_id", "principals", ["agent_id"])

    principals = sa.table(
        "principals",
        sa.column("id", sa.String),
        sa.column("workspace_id", sa.String),
        sa.column("agent_id", sa.String),
        sa.column("type", sa.String),
        sa.column("display_name", sa.String),
        sa.column("external_id", sa.String),
        sa.column("status", sa.String),
    )
    op.bulk_insert(
        principals,
        [
            {
                "id": DATA_AGENT_SERVICE_ACCOUNT_ID,
                "workspace_id": WORKSPACE_ID,
                "agent_id": DATA_AGENT_ID,
                "type": "service_account",
                "display_name": "Data Agent Runtime",
                "external_id": "data-agent-runtime",
                "status": "active",
            }
        ],
    )
    principal_roles = sa.table(
        "principal_roles",
        sa.column("principal_id", sa.String),
        sa.column("role_id", sa.String),
    )
    op.bulk_insert(
        principal_roles,
        [
            {
                "principal_id": DATA_AGENT_SERVICE_ACCOUNT_ID,
                "role_id": DATA_ANALYST_ROLE_ID,
            }
        ],
    )


def downgrade() -> None:
    op.execute(
        sa.text("DELETE FROM principal_roles WHERE principal_id = :principal_id").bindparams(
            principal_id=DATA_AGENT_SERVICE_ACCOUNT_ID
        )
    )
    op.execute(
        sa.text("DELETE FROM principals WHERE id = :principal_id").bindparams(
            principal_id=DATA_AGENT_SERVICE_ACCOUNT_ID
        )
    )
    op.drop_index("ix_principals_agent_id", table_name="principals")
    op.drop_constraint("fk_principals_agent_id", "principals", type_="foreignkey")
    op.drop_column("principals", "agent_id")
