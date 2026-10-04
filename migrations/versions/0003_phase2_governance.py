"""create phase 2 governance and SQL tools

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-03
"""

import json
from collections.abc import Sequence
from hashlib import sha256

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

WORKSPACE_ID = "00000000-0000-0000-0000-000000000001"
DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"

ADMIN_PRINCIPAL_ID = "00000000-0000-0000-0000-000000000501"
ANALYST_PRINCIPAL_ID = "00000000-0000-0000-0000-000000000502"
VIEWER_PRINCIPAL_ID = "00000000-0000-0000-0000-000000000503"
ADMIN_ROLE_ID = "00000000-0000-0000-0000-000000000601"
ANALYST_ROLE_ID = "00000000-0000-0000-0000-000000000602"
VIEWER_ROLE_ID = "00000000-0000-0000-0000-000000000603"
INVOKE_PERMISSION_ID = "00000000-0000-0000-0000-000000000701"
DATABASE_PERMISSION_ID = "00000000-0000-0000-0000-000000000702"
HIGH_RISK_PERMISSION_ID = "00000000-0000-0000-0000-000000000703"
ADMIN_PERMISSION_ID = "00000000-0000-0000-0000-000000000704"

LIST_TABLES_TOOL_ID = "00000000-0000-0000-0000-000000000211"
DESCRIBE_TABLE_TOOL_ID = "00000000-0000-0000-0000-000000000212"
QUERY_TOOL_ID = "00000000-0000-0000-0000-000000000213"
LIST_TABLES_VERSION_ID = "00000000-0000-0000-0000-000000000311"
DESCRIBE_TABLE_VERSION_ID = "00000000-0000-0000-0000-000000000312"
QUERY_VERSION_ID = "00000000-0000-0000-0000-000000000313"
LIST_TABLES_BINDING_ID = "00000000-0000-0000-0000-000000000411"
DESCRIBE_TABLE_BINDING_ID = "00000000-0000-0000-0000-000000000412"
QUERY_BINDING_ID = "00000000-0000-0000-0000-000000000413"

SCHEMA_PROPERTY = {"type": "string", "minLength": 1, "maxLength": 63, "default": "public"}
SQL_TOOL_DEFINITIONS = [
    {
        "tool_id": LIST_TABLES_TOOL_ID,
        "version_id": LIST_TABLES_VERSION_ID,
        "binding_id": LIST_TABLES_BINDING_ID,
        "name": "list_tables",
        "display_name": "List Tables",
        "description": "List tables and views in an allowed PostgreSQL schema.",
        "risk_level": "low",
        "handler_key": "sql.list_tables",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {"schema": SCHEMA_PROPERTY},
        },
        "output_schema": {
            "type": "object",
            "required": ["schema", "tables"],
            "properties": {"schema": {"type": "string"}, "tables": {"type": "array"}},
        },
    },
    {
        "tool_id": DESCRIBE_TABLE_TOOL_ID,
        "version_id": DESCRIBE_TABLE_VERSION_ID,
        "binding_id": DESCRIBE_TABLE_BINDING_ID,
        "name": "describe_table",
        "display_name": "Describe Table",
        "description": "Describe columns for one table in an allowed PostgreSQL schema.",
        "risk_level": "low",
        "handler_key": "sql.describe_table",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["table"],
            "properties": {
                "schema": SCHEMA_PROPERTY,
                "table": {"type": "string", "minLength": 1, "maxLength": 63},
            },
        },
        "output_schema": {
            "type": "object",
            "required": ["schema", "table", "columns"],
            "properties": {
                "schema": {"type": "string"},
                "table": {"type": "string"},
                "columns": {"type": "array"},
            },
        },
    },
    {
        "tool_id": QUERY_TOOL_ID,
        "version_id": QUERY_VERSION_ID,
        "binding_id": QUERY_BINDING_ID,
        "name": "query_readonly",
        "display_name": "Read-only SQL Query",
        "description": "Execute one parsed, bounded and read-only PostgreSQL query.",
        "risk_level": "medium",
        "handler_key": "sql.query_readonly",
        "input_schema": {
            "type": "object",
            "additionalProperties": False,
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "minLength": 1, "maxLength": 20000},
                "max_rows": {"type": "integer", "minimum": 1, "maximum": 1000},
            },
        },
        "output_schema": {
            "type": "object",
            "required": ["columns", "rows", "row_count", "truncated"],
            "properties": {
                "columns": {"type": "array"},
                "rows": {"type": "array"},
                "row_count": {"type": "integer"},
                "truncated": {"type": "boolean"},
            },
        },
    },
]


def definition_hash(definition: dict[str, object]) -> str:
    payload = {
        "input_schema": definition["input_schema"],
        "output_schema": definition["output_schema"],
        "executor_type": "native",
        "executor_config": {"handler_key": definition["handler_key"]},
        "required_permissions": ["database.read"],
    }
    return sha256(json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def upgrade() -> None:
    op.create_table(
        "principals",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("type", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("external_id", sa.String(length=160), nullable=False),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "external_id", name="uq_principals_external_id"),
    )
    op.create_index("ix_principals_workspace_id", "principals", ["workspace_id"])

    op.create_table(
        "roles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("workspace_id", "name", name="uq_roles_workspace_name"),
    )
    op.create_index("ix_roles_workspace_id", "roles", ["workspace_id"])

    op.create_table(
        "permissions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("key", sa.String(length=120), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index("ix_permissions_key", "permissions", ["key"], unique=True)

    op.create_table(
        "role_permissions",
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.Column("permission_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["permission_id"], ["permissions.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("role_id", "permission_id"),
    )
    op.create_table(
        "principal_roles",
        sa.Column("principal_id", sa.String(length=36), nullable=False),
        sa.Column("role_id", sa.String(length=36), nullable=False),
        sa.ForeignKeyConstraint(["principal_id"], ["principals.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("principal_id", "role_id"),
    )
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("workspace_id", sa.String(length=36), nullable=False),
        sa.Column("actor_principal_id", sa.String(length=36), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("resource_type", sa.String(length=80), nullable=False),
        sa.Column("resource_id", sa.String(length=80), nullable=False),
        sa.Column("decision", sa.String(length=24), nullable=False),
        sa.Column("metadata_redacted", sa.JSON(), nullable=False),
        sa.Column("trace_id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["actor_principal_id"], ["principals.id"]),
        sa.ForeignKeyConstraint(["workspace_id"], ["workspaces.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_audit_events_workspace_id", "audit_events", ["workspace_id"])
    op.create_index("ix_audit_events_actor_principal_id", "audit_events", ["actor_principal_id"])
    op.create_index("ix_audit_events_action", "audit_events", ["action"])
    op.create_index("ix_audit_events_decision", "audit_events", ["decision"])
    op.create_index("ix_audit_events_trace_id", "audit_events", ["trace_id"])

    op.add_column("executions", sa.Column("principal_id", sa.String(length=36), nullable=True))
    op.add_column("executions", sa.Column("policy_decision", sa.JSON(), nullable=True))
    op.add_column(
        "executions",
        sa.Column("attempts", sa.Integer(), server_default="1", nullable=False),
    )
    op.create_foreign_key(
        "fk_executions_principal_id", "executions", "principals", ["principal_id"], ["id"]
    )
    op.create_index("ix_executions_principal_id", "executions", ["principal_id"])

    connection = op.get_bind()
    workspace_id = connection.execute(
        sa.text("SELECT id FROM workspaces WHERE slug = 'default'")
    ).scalar_one_or_none()
    if workspace_id is None:
        raise RuntimeError("Default workspace is required before applying Phase 2 migration.")
    data_agent_id = connection.execute(
        sa.text("SELECT id FROM agents WHERE namespace = 'platform' AND name = 'data-agent'")
    ).scalar_one_or_none()
    if data_agent_id is None:
        raise RuntimeError("Data Agent is required before applying Phase 2 migration.")

    principals = sa.table(
        "principals",
        sa.column("id", sa.String), sa.column("workspace_id", sa.String),
        sa.column("type", sa.String), sa.column("display_name", sa.String),
        sa.column("external_id", sa.String), sa.column("status", sa.String),
    )
    op.bulk_insert(principals, [
        {"id": ADMIN_PRINCIPAL_ID, "workspace_id": workspace_id, "type": "user", "display_name": "Local Admin", "external_id": "local-admin", "status": "active"},
        {"id": ANALYST_PRINCIPAL_ID, "workspace_id": workspace_id, "type": "user", "display_name": "Local Data Analyst", "external_id": "local-analyst", "status": "active"},
        {"id": VIEWER_PRINCIPAL_ID, "workspace_id": workspace_id, "type": "user", "display_name": "Local Viewer", "external_id": "local-viewer", "status": "active"},
    ])
    roles = sa.table(
        "roles", sa.column("id", sa.String), sa.column("workspace_id", sa.String),
        sa.column("name", sa.String), sa.column("description", sa.Text),
    )
    op.bulk_insert(roles, [
        {"id": ADMIN_ROLE_ID, "workspace_id": workspace_id, "name": "platform-admin", "description": "Full local platform administration."},
        {"id": ANALYST_ROLE_ID, "workspace_id": workspace_id, "name": "data-analyst", "description": "Invoke tools and read governed data."},
        {"id": VIEWER_ROLE_ID, "workspace_id": workspace_id, "name": "tool-user", "description": "Invoke low-risk tools without database access."},
    ])
    permissions = sa.table(
        "permissions", sa.column("id", sa.String), sa.column("key", sa.String),
        sa.column("description", sa.Text),
    )
    op.bulk_insert(permissions, [
        {"id": INVOKE_PERMISSION_ID, "key": "tool.invoke", "description": "Invoke an enabled Tool through the Gateway."},
        {"id": DATABASE_PERMISSION_ID, "key": "database.read", "description": "Read an approved database source."},
        {"id": HIGH_RISK_PERMISSION_ID, "key": "tool.high_risk.invoke", "description": "Invoke high-risk Tools."},
        {"id": ADMIN_PERMISSION_ID, "key": "platform.admin", "description": "Manage catalog and policy configuration."},
    ])
    role_permission_table = sa.table(
        "role_permissions", sa.column("role_id", sa.String), sa.column("permission_id", sa.String)
    )
    op.bulk_insert(role_permission_table, [
        {"role_id": ADMIN_ROLE_ID, "permission_id": permission_id}
        for permission_id in [INVOKE_PERMISSION_ID, DATABASE_PERMISSION_ID, HIGH_RISK_PERMISSION_ID, ADMIN_PERMISSION_ID]
    ] + [
        {"role_id": ANALYST_ROLE_ID, "permission_id": INVOKE_PERMISSION_ID},
        {"role_id": ANALYST_ROLE_ID, "permission_id": DATABASE_PERMISSION_ID},
        {"role_id": VIEWER_ROLE_ID, "permission_id": INVOKE_PERMISSION_ID},
    ])
    principal_role_table = sa.table(
        "principal_roles", sa.column("principal_id", sa.String), sa.column("role_id", sa.String)
    )
    op.bulk_insert(principal_role_table, [
        {"principal_id": ADMIN_PRINCIPAL_ID, "role_id": ADMIN_ROLE_ID},
        {"principal_id": ANALYST_PRINCIPAL_ID, "role_id": ANALYST_ROLE_ID},
        {"principal_id": VIEWER_PRINCIPAL_ID, "role_id": VIEWER_ROLE_ID},
    ])
    connection.execute(
        sa.text("UPDATE executions SET principal_id = :principal_id WHERE principal_id IS NULL"),
        {"principal_id": ADMIN_PRINCIPAL_ID},
    )

    tools = sa.table(
        "tools", sa.column("id", sa.String), sa.column("workspace_id", sa.String),
        sa.column("namespace", sa.String), sa.column("name", sa.String),
        sa.column("display_name", sa.String), sa.column("description", sa.Text),
        sa.column("owner", sa.String), sa.column("provider_type", sa.String),
        sa.column("risk_level", sa.String), sa.column("status", sa.String),
        sa.column("default_version", sa.String),
    )
    op.bulk_insert(tools, [
        {"id": item["tool_id"], "workspace_id": workspace_id, "namespace": "sql", "name": item["name"], "display_name": item["display_name"], "description": item["description"], "owner": "Tool Platform", "provider_type": "native", "risk_level": item["risk_level"], "status": "active", "default_version": "1.0.0"}
        for item in SQL_TOOL_DEFINITIONS
    ])
    versions = sa.table(
        "tool_versions", sa.column("id", sa.String), sa.column("tool_id", sa.String),
        sa.column("version", sa.String), sa.column("input_schema", sa.JSON),
        sa.column("output_schema", sa.JSON), sa.column("executor_type", sa.String),
        sa.column("executor_config", sa.JSON), sa.column("timeout_seconds", sa.Integer),
        sa.column("retry_policy", sa.JSON), sa.column("required_permissions", sa.JSON),
        sa.column("definition_hash", sa.String), sa.column("registration_channel", sa.String),
    )
    op.bulk_insert(versions, [
        {"id": item["version_id"], "tool_id": item["tool_id"], "version": "1.0.0", "input_schema": item["input_schema"], "output_schema": item["output_schema"], "executor_type": "native", "executor_config": {"handler_key": item["handler_key"]}, "timeout_seconds": 8, "retry_policy": {"max_attempts": 2, "retry_safe": True}, "required_permissions": ["database.read"], "definition_hash": definition_hash(item), "registration_channel": "seed"}
        for item in SQL_TOOL_DEFINITIONS
    ])
    bindings = sa.table(
        "agent_tool_bindings", sa.column("id", sa.String), sa.column("agent_id", sa.String),
        sa.column("tool_id", sa.String), sa.column("version_policy", sa.String),
        sa.column("enabled", sa.Boolean), sa.column("configuration", sa.JSON),
    )
    op.bulk_insert(bindings, [
        {"id": item["binding_id"], "agent_id": data_agent_id, "tool_id": item["tool_id"], "version_policy": "default", "enabled": True, "configuration": {}}
        for item in SQL_TOOL_DEFINITIONS
    ])


def downgrade() -> None:
    sql_tool_ids = [LIST_TABLES_TOOL_ID, DESCRIBE_TABLE_TOOL_ID, QUERY_TOOL_ID]
    connection = op.get_bind()
    connection.execute(sa.text("DELETE FROM executions WHERE tool_id IN :tool_ids").bindparams(sa.bindparam("tool_ids", expanding=True)), {"tool_ids": sql_tool_ids})
    connection.execute(sa.text("DELETE FROM agent_tool_bindings WHERE tool_id IN :tool_ids").bindparams(sa.bindparam("tool_ids", expanding=True)), {"tool_ids": sql_tool_ids})
    connection.execute(sa.text("DELETE FROM tool_versions WHERE tool_id IN :tool_ids").bindparams(sa.bindparam("tool_ids", expanding=True)), {"tool_ids": sql_tool_ids})
    connection.execute(sa.text("DELETE FROM tools WHERE id IN :tool_ids").bindparams(sa.bindparam("tool_ids", expanding=True)), {"tool_ids": sql_tool_ids})
    op.drop_index("ix_executions_principal_id", table_name="executions")
    op.drop_constraint("fk_executions_principal_id", "executions", type_="foreignkey")
    op.drop_column("executions", "attempts")
    op.drop_column("executions", "policy_decision")
    op.drop_column("executions", "principal_id")
    op.drop_index("ix_audit_events_trace_id", table_name="audit_events")
    op.drop_index("ix_audit_events_decision", table_name="audit_events")
    op.drop_index("ix_audit_events_action", table_name="audit_events")
    op.drop_index("ix_audit_events_actor_principal_id", table_name="audit_events")
    op.drop_index("ix_audit_events_workspace_id", table_name="audit_events")
    op.drop_table("audit_events")
    op.drop_table("principal_roles")
    op.drop_table("role_permissions")
    op.drop_index("ix_permissions_key", table_name="permissions")
    op.drop_table("permissions")
    op.drop_index("ix_roles_workspace_id", table_name="roles")
    op.drop_table("roles")
    op.drop_index("ix_principals_workspace_id", table_name="principals")
    op.drop_table("principals")
