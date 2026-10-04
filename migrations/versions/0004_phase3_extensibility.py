"""create phase 3 extensibility models and demo catalog entries

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-03
"""

import json
from collections.abc import Sequence
from hashlib import sha256

import sqlalchemy as sa
from alembic import op

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
OPERATIONS_AGENT_ID = "00000000-0000-0000-0000-000000000103"
SECURITY_AGENT_ID = "00000000-0000-0000-0000-000000000104"
HTTP_TOOL_ID = "00000000-0000-0000-0000-000000000214"
HTTP_VERSION_ID = "00000000-0000-0000-0000-000000000314"
HTTP_BINDING_ID = "00000000-0000-0000-0000-000000000414"

HTTP_INPUT_SCHEMA = {"type": "object", "additionalProperties": False}
HTTP_OUTPUT_SCHEMA = {
    "type": "object",
    "required": ["status_code", "body"],
    "properties": {
        "status_code": {"type": "integer"},
        "body": {},
        "content_type": {"type": "string"},
    },
}
HTTP_EXECUTOR_CONFIG = {
    "method": "GET",
    "url_setting": "http_health_check_url",
    "pass_arguments": False,
}


def definition_hash() -> str:
    payload = {
        "input_schema": HTTP_INPUT_SCHEMA,
        "output_schema": HTTP_OUTPUT_SCHEMA,
        "executor_type": "http",
        "executor_config": HTTP_EXECUTOR_CONFIG,
        "timeout_seconds": 5,
        "retry_policy": {"max_attempts": 2, "retry_safe": True},
        "required_permissions": [],
    }
    serialized = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return sha256(serialized.encode()).hexdigest()


def upgrade() -> None:
    op.create_table(
        "mcp_servers",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("transport", sa.String(length=32), nullable=False),
        sa.Column("endpoint", sa.String(length=500), nullable=False),
        sa.Column("auth_secret_ref", sa.String(length=200), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("discovery_snapshot", sa.JSON(), nullable=False),
        sa.Column("last_discovered_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_safe", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_mcp_servers_workspace_name"),
    )
    op.create_index("ix_mcp_servers_workspace_id", "mcp_servers", ["workspace_id"])

    agents = sa.table(
        "agents",
        sa.column("id", sa.String),
        sa.column("workspace_id", sa.String),
        sa.column("namespace", sa.String),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("agent_type", sa.String),
        sa.column("status", sa.String),
        sa.column("owner", sa.String),
    )
    op.bulk_insert(
        agents,
        [
            {
                "id": OPERATIONS_AGENT_ID,
                "workspace_id": WORKSPACE_ID,
                "namespace": "platform",
                "name": "operations-agent",
                "display_name": "Operations Agent",
                "description": "Monitors services and demonstrates reusable HTTP tools.",
                "agent_type": "operations",
                "status": "active",
                "owner": "Operations Platform",
            },
            {
                "id": SECURITY_AGENT_ID,
                "workspace_id": WORKSPACE_ID,
                "namespace": "platform",
                "name": "security-agent",
                "display_name": "Security Agent",
                "description": "Represents cross-platform policy and security consumers.",
                "agent_type": "security",
                "status": "active",
                "owner": "Security Platform",
            },
        ],
    )

    tools = sa.table(
        "tools",
        sa.column("id", sa.String),
        sa.column("workspace_id", sa.String),
        sa.column("namespace", sa.String),
        sa.column("name", sa.String),
        sa.column("display_name", sa.String),
        sa.column("description", sa.Text),
        sa.column("owner", sa.String),
        sa.column("provider_type", sa.String),
        sa.column("risk_level", sa.String),
        sa.column("status", sa.String),
        sa.column("default_version", sa.String),
    )
    op.bulk_insert(
        tools,
        [
            {
                "id": HTTP_TOOL_ID,
                "workspace_id": WORKSPACE_ID,
                "namespace": "http",
                "name": "health_check",
                "display_name": "HTTP Health Check",
                "description": "Check an allowlisted HTTP service through the HttpExecutor.",
                "owner": "Tool Platform",
                "provider_type": "http",
                "risk_level": "low",
                "status": "active",
                "default_version": "1.0.0",
            }
        ],
    )

    versions = sa.table(
        "tool_versions",
        sa.column("id", sa.String),
        sa.column("tool_id", sa.String),
        sa.column("version", sa.String),
        sa.column("input_schema", sa.JSON),
        sa.column("output_schema", sa.JSON),
        sa.column("executor_type", sa.String),
        sa.column("executor_config", sa.JSON),
        sa.column("timeout_seconds", sa.Integer),
        sa.column("retry_policy", sa.JSON),
        sa.column("required_permissions", sa.JSON),
        sa.column("definition_hash", sa.String),
        sa.column("registration_channel", sa.String),
    )
    op.bulk_insert(
        versions,
        [
            {
                "id": HTTP_VERSION_ID,
                "tool_id": HTTP_TOOL_ID,
                "version": "1.0.0",
                "input_schema": HTTP_INPUT_SCHEMA,
                "output_schema": HTTP_OUTPUT_SCHEMA,
                "executor_type": "http",
                "executor_config": HTTP_EXECUTOR_CONFIG,
                "timeout_seconds": 5,
                "retry_policy": {"max_attempts": 2, "retry_safe": True},
                "required_permissions": [],
                "definition_hash": definition_hash(),
                "registration_channel": "seed",
            }
        ],
    )

    bindings = sa.table(
        "agent_tool_bindings",
        sa.column("id", sa.String),
        sa.column("agent_id", sa.String),
        sa.column("tool_id", sa.String),
        sa.column("version_policy", sa.String),
        sa.column("enabled", sa.Boolean),
        sa.column("configuration", sa.JSON),
    )
    op.bulk_insert(
        bindings,
        [
            {
                "id": HTTP_BINDING_ID,
                "agent_id": OPERATIONS_AGENT_ID,
                "tool_id": HTTP_TOOL_ID,
                "version_policy": "default",
                "enabled": True,
                "configuration": {},
            }
        ],
    )


def downgrade() -> None:
    op.execute(sa.text("DELETE FROM agent_tool_bindings WHERE id = :id").bindparams(id=HTTP_BINDING_ID))
    op.execute(sa.text("DELETE FROM tool_versions WHERE id = :id").bindparams(id=HTTP_VERSION_ID))
    op.execute(sa.text("DELETE FROM tools WHERE id = :id").bindparams(id=HTTP_TOOL_ID))
    op.execute(
        sa.text("DELETE FROM agents WHERE id IN (:operations_id, :security_id)").bindparams(
            operations_id=OPERATIONS_AGENT_ID, security_id=SECURITY_AGENT_ID
        )
    )
    op.drop_index("ix_mcp_servers_workspace_id", table_name="mcp_servers")
    op.drop_table("mcp_servers")
