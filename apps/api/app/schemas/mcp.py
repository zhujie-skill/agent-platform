from datetime import datetime
from typing import Any, Literal

from pydantic import AnyHttpUrl, BaseModel, Field, field_validator


class McpServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    transport: Literal["streamable_http"] = "streamable_http"
    endpoint: AnyHttpUrl
    auth_secret_ref: str | None = Field(default=None, max_length=200)

    @field_validator("auth_secret_ref")
    @classmethod
    def validate_secret_ref(cls, value: str | None) -> str | None:
        if value is not None and not value.startswith("env:"):
            raise ValueError("auth_secret_ref must use the env:VARIABLE format")
        return value


class DiscoveredMcpTool(BaseModel):
    name: str
    title: str | None
    description: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any] | None
    import_state: Literal["new", "unchanged", "changed"] = "new"


class McpServerRead(BaseModel):
    id: str
    name: str
    transport: str
    endpoint: str
    auth_secret_ref: str | None
    status: str
    discovery_snapshot: list[DiscoveredMcpTool]
    last_discovered_at: datetime | None
    last_error_safe: str | None
    created_at: datetime


class McpToolImport(BaseModel):
    remote_tool_name: str = Field(min_length=1, max_length=160)
    namespace: str = Field(default="external", pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    owner: str = Field(default="External MCP", min_length=1, max_length=120)
    risk_level: Literal["low", "medium", "high"] = "low"
    required_permissions: list[str] = Field(default_factory=list)
    make_default: bool = True
