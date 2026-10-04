"""create phase 1 agent and tool catalog

Revision ID: 0002
Revises: 0001
Create Date: 2026-10-02
"""

import json
from collections.abc import Sequence
from hashlib import sha256

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"
DEVELOPER_AGENT_ID = "00000000-0000-0000-0000-000000000102"
ECHO_TOOL_ID = "00000000-0000-0000-0000-000000000201"
ECHO_VERSION_ID = "00000000-0000-0000-0000-000000000301"
DATA_ECHO_BINDING_ID = "00000000-0000-0000-0000-000000000401"
DEVELOPER_ECHO_BINDING_ID = "00000000-0000-0000-0000-000000000402"

ECHO_INPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["message"],
    "properties": {"message": {"type": "string", "minLength": 1, "maxLength": 2000}},
}
ECHO_OUTPUT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["message"],
    "properties": {"message": {"type": "string"}},
}


def definition_hash() -> str:
    payload = {
        "input_schema": ECHO_INPUT_SCHEMA,
        "output_schema": ECHO_OUTPUT_SCHEMA,
        "executor_type": "native",
        "executor_config": {"handler_key": "system.echo"},
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("agent_type", sa.String(length=40), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "namespace", "name", name="uq_agents_identity"),
    )
    op.create_index("ix_agents_workspace_id", "agents", ["workspace_id"])

    op.create_table(
        "tools",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("namespace", sa.String(length=80), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("owner", sa.String(length=120), nullable=False),
        sa.Column("provider_type", sa.String(length=24), nullable=False),
        sa.Column("risk_level", sa.String(length=24), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("default_version", sa.String(length=40), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "namespace", "name", name="uq_tools_identity"),
    )
    op.create_index("ix_tools_workspace_id", "tools", ["workspace_id"])

    op.create_table(
        "tool_versions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("tool_id", sa.String(length=36), nullable=False),
        sa.Column("version", sa.String(length=40), nullable=False),
        sa.Column("input_schema", sa.JSON(), nullable=False),
        sa.Column("output_schema", sa.JSON(), nullable=False),
        sa.Column("executor_type", sa.String(length=24), nullable=False),
        sa.Column("executor_config", sa.JSON(), nullable=False),
        sa.Column("timeout_seconds", sa.Integer(), nullable=False),
        sa.Column("retry_policy", sa.JSON(), nullable=False),
        sa.Column("required_permissions", sa.JSON(), nullable=False),
        sa.Column("definition_hash", sa.String(length=64), nullable=False),
        sa.Column("registration_channel", sa.String(length=24), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("deprecated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tool_id", "version", name="uq_tool_versions_tool_version"),
    )
    op.create_index("ix_tool_versions_tool_id", "tool_versions", ["tool_id"])

    op.create_table(
        "agent_tool_bindings",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("tool_id", sa.String(length=36), nullable=False),
        sa.Column("version_policy", sa.String(length=80), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column("configuration", sa.JSON(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("agent_id", "tool_id", name="uq_agent_tool_bindings_pair"),
    )
    op.create_index("ix_agent_tool_bindings_agent_id", "agent_tool_bindings", ["agent_id"])
    op.create_index("ix_agent_tool_bindings_tool_id", "agent_tool_bindings", ["tool_id"])

    op.create_table(
        "executions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("agent_id", sa.String(length=36), nullable=False),
        sa.Column("agent_tool_binding_id", sa.String(length=36), nullable=False),
        sa.Column("tool_id", sa.String(length=36), nullable=False),
        sa.Column("tool_version_id", sa.String(length=36), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("request_source", sa.String(length=80), nullable=False),
        sa.Column("arguments_redacted", sa.JSON(), nullable=False),
        sa.Column("result_redacted", sa.JSON(), nullable=True),
        sa.Column("error_code", sa.String(length=80), nullable=True),
        sa.Column("error_message_safe", sa.Text(), nullable=True),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("idempotency_key", sa.String(length=160), nullable=True),
        sa.Column(
            "started_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["agent_id"], ["agents.id"]),
        sa.ForeignKeyConstraint(["agent_tool_binding_id"], ["agent_tool_bindings.id"]),
        sa.ForeignKeyConstraint(["tool_id"], ["tools.id"]),
        sa.ForeignKeyConstraint(["tool_version_id"], ["tool_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_executions_workspace_id", "executions", ["workspace_id"])
    op.create_index("ix_executions_agent_id", "executions", ["agent_id"])
    op.create_index("ix_executions_tool_id", "executions", ["tool_id"])
    op.create_index("ix_executions_trace_id", "executions", ["trace_id"])

    connection = op.get_bind()
    workspace_exists = connection.execute(
        sa.text("SELECT id FROM workspaces WHERE slug = :slug"), {"slug": "default"}
    ).scalar_one_or_none()
    workspace_id = workspace_exists or WORKSPACE_ID
    if workspace_exists is None:
        connection.execute(
            sa.text(
                "INSERT INTO workspaces (id, name, slug) VALUES (:id, :name, :slug)"
            ),
            {"id": workspace_id, "name": "Default Workspace", "slug": "default"},
        )

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
                "id": DATA_AGENT_ID,
                "workspace_id": workspace_id,
                "namespace": "platform",
                "name": "data-agent",
                "display_name": "Data Agent",
                "description": "Discover and query governed data through reusable tools.",
                "agent_type": "data",
                "status": "active",
                "owner": "Data Platform",
            },
            {
                "id": DEVELOPER_AGENT_ID,
                "workspace_id": workspace_id,
                "namespace": "platform",
                "name": "developer-agent",
                "display_name": "Developer Agent",
                "description": "Assist engineering work through governed repository tools.",
                "agent_type": "developer",
                "status": "active",
                "owner": "Developer Platform",
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
                "id": ECHO_TOOL_ID,
                "workspace_id": workspace_id,
                "namespace": "system",
                "name": "echo",
                "display_name": "Echo",
                "description": "Return the input message to prove the complete execution path.",
                "owner": "Tool Platform",
                "provider_type": "native",
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
                "id": ECHO_VERSION_ID,
                "tool_id": ECHO_TOOL_ID,
                "version": "1.0.0",
                "input_schema": ECHO_INPUT_SCHEMA,
                "output_schema": ECHO_OUTPUT_SCHEMA,
                "executor_type": "native",
                "executor_config": {"handler_key": "system.echo"},
                "timeout_seconds": 5,
                "retry_policy": {"max_attempts": 1},
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
                "id": DATA_ECHO_BINDING_ID,
                "agent_id": DATA_AGENT_ID,
                "tool_id": ECHO_TOOL_ID,
                "version_policy": "default",
                "enabled": True,
                "configuration": {},
            },
            {
                "id": DEVELOPER_ECHO_BINDING_ID,
                "agent_id": DEVELOPER_AGENT_ID,
                "tool_id": ECHO_TOOL_ID,
                "version_policy": "default",
                "enabled": True,
                "configuration": {},
            },
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_executions_trace_id", table_name="executions")
    op.drop_index("ix_executions_tool_id", table_name="executions")
    op.drop_index("ix_executions_agent_id", table_name="executions")
    op.drop_index("ix_executions_workspace_id", table_name="executions")
    op.drop_table("executions")
    op.drop_index("ix_agent_tool_bindings_tool_id", table_name="agent_tool_bindings")
    op.drop_index("ix_agent_tool_bindings_agent_id", table_name="agent_tool_bindings")
    op.drop_table("agent_tool_bindings")
    op.drop_index("ix_tool_versions_tool_id", table_name="tool_versions")
    op.drop_table("tool_versions")
    op.drop_index("ix_tools_workspace_id", table_name="tools")
    op.drop_table("tools")
    op.drop_index("ix_agents_workspace_id", table_name="agents")
    op.drop_table("agents")
