from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


def new_id() -> str:
    return str(uuid4())


class Agent(Base):
    __tablename__ = "agents"
    __table_args__ = (
        UniqueConstraint("workspace_id", "namespace", "name", name="uq_agents_identity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    agent_type: Mapped[str] = mapped_column(String(40), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    tool_bindings: Mapped[list[AgentToolBinding]] = relationship(
        back_populates="agent", cascade="all, delete-orphan"
    )


class Tool(Base):
    __tablename__ = "tools"
    __table_args__ = (
        UniqueConstraint("workspace_id", "namespace", "name", name="uq_tools_identity"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    namespace: Mapped[str] = mapped_column(String(80), nullable=False)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    provider_type: Mapped[str] = mapped_column(String(24), nullable=False)
    risk_level: Mapped[str] = mapped_column(String(24), nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False, default="active")
    default_version: Mapped[str | None] = mapped_column(String(40))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    versions: Mapped[list[ToolVersion]] = relationship(
        back_populates="tool", cascade="all, delete-orphan"
    )
    agent_bindings: Mapped[list[AgentToolBinding]] = relationship(
        back_populates="tool", cascade="all, delete-orphan"
    )


class ToolVersion(Base):
    __tablename__ = "tool_versions"
    __table_args__ = (
        UniqueConstraint("tool_id", "version", name="uq_tool_versions_tool_version"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    tool_id: Mapped[str] = mapped_column(
        ForeignKey("tools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version: Mapped[str] = mapped_column(String(40), nullable=False)
    input_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    output_schema: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    executor_type: Mapped[str] = mapped_column(String(24), nullable=False)
    executor_config: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    timeout_seconds: Mapped[int] = mapped_column(Integer, nullable=False, default=10)
    retry_policy: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    required_permissions: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    definition_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    registration_channel: Mapped[str] = mapped_column(String(24), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    tool: Mapped[Tool] = relationship(back_populates="versions")


class AgentToolBinding(Base):
    __tablename__ = "agent_tool_bindings"
    __table_args__ = (
        UniqueConstraint("agent_id", "tool_id", name="uq_agent_tool_bindings_pair"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    agent_id: Mapped[str] = mapped_column(
        ForeignKey("agents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tool_id: Mapped[str] = mapped_column(
        ForeignKey("tools.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_policy: Mapped[str] = mapped_column(String(80), nullable=False, default="default")
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    configuration: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    agent: Mapped[Agent] = relationship(back_populates="tool_bindings")
    tool: Mapped[Tool] = relationship(back_populates="agent_bindings")


class Execution(Base):
    __tablename__ = "executions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    workspace_id: Mapped[str] = mapped_column(
        ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    agent_id: Mapped[str] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    agent_tool_binding_id: Mapped[str] = mapped_column(
        ForeignKey("agent_tool_bindings.id"), nullable=False
    )
    tool_id: Mapped[str] = mapped_column(ForeignKey("tools.id"), nullable=False, index=True)
    tool_version_id: Mapped[str] = mapped_column(
        ForeignKey("tool_versions.id"), nullable=False
    )
    principal_id: Mapped[str | None] = mapped_column(
        ForeignKey("principals.id"), nullable=True, index=True
    )
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    request_source: Mapped[str] = mapped_column(String(80), nullable=False)
    arguments_redacted: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    result_redacted: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error_code: Mapped[str | None] = mapped_column(String(80))
    error_message_safe: Mapped[str | None] = mapped_column(Text)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(160))
    policy_decision: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    duration_ms: Mapped[int | None] = mapped_column(Integer)
