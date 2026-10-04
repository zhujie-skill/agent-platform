from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolReference(BaseModel):
    id: str
    namespace: str
    name: str
    display_name: str
    provider_type: str
    status: str
    version_policy: str
    binding_enabled: bool


class AgentReference(BaseModel):
    id: str
    namespace: str
    name: str
    display_name: str
    status: str
    version_policy: str
    binding_enabled: bool


class AgentCreate(BaseModel):
    namespace: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    agent_type: str = Field(min_length=1, max_length=40)
    owner: str = Field(min_length=1, max_length=120)


class AgentRead(BaseModel):
    id: str
    namespace: str
    name: str
    display_name: str
    description: str
    agent_type: str
    status: str
    owner: str
    created_at: datetime
    tools: list[ToolReference]


class ToolVersionCreate(BaseModel):
    version: str = Field(min_length=1, max_length=40, pattern=r"^\d+\.\d+\.\d+$")
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    handler_key: str = Field(min_length=1, max_length=160)
    timeout_seconds: int = Field(default=10, ge=1, le=300)
    retry_policy: dict[str, Any] = Field(default_factory=lambda: {"max_attempts": 1})
    required_permissions: list[str] = Field(default_factory=list)
    registration_channel: Literal["console", "api", "seed"] = "api"
    make_default: bool = True


class ToolCreate(BaseModel):
    namespace: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    name: str = Field(min_length=1, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]*$")
    display_name: str = Field(min_length=1, max_length=120)
    description: str = Field(min_length=1, max_length=2000)
    owner: str = Field(min_length=1, max_length=120)
    provider_type: Literal["native"] = "native"
    risk_level: Literal["low", "medium", "high"] = "low"
    version: ToolVersionCreate


class ToolUpdate(BaseModel):
    status: Literal["active", "disabled"] | None = None
    default_version: str | None = Field(default=None, max_length=40)


class AvailableToolRead(BaseModel):
    id: str
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    version: str
    provider_type: str
    risk_level: str


class ToolVersionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    executor_type: str
    executor_config: dict[str, Any]
    timeout_seconds: int
    retry_policy: dict[str, Any]
    required_permissions: list[str]
    definition_hash: str
    registration_channel: str
    created_at: datetime
    deprecated_at: datetime | None


class ToolRead(BaseModel):
    id: str
    namespace: str
    name: str
    display_name: str
    description: str
    owner: str
    provider_type: str
    risk_level: str
    status: str
    default_version: str | None
    created_at: datetime
    versions: list[ToolVersionRead]
    consumer_agents: list[AgentReference]


class BindingUpdate(BaseModel):
    version_policy: str = Field(default="default", min_length=1, max_length=80)
    enabled: bool = True
    configuration: dict[str, Any] = Field(default_factory=dict)

    @field_validator("version_policy")
    @classmethod
    def validate_version_policy(cls, value: str) -> str:
        if value == "default" or value.startswith("exact:"):
            return value
        raise ValueError("version_policy must be 'default' or 'exact:<semver>'")


class InvokeContext(BaseModel):
    agent_id: str
    request_source: str = Field(default="api", min_length=1, max_length=80)
    idempotency_key: str | None = Field(default=None, max_length=160)


class InvokeRequest(BaseModel):
    version: str | None = None
    arguments: dict[str, Any]
    context: InvokeContext


class InvokeMeta(BaseModel):
    principal: str
    agent: str
    tool: str
    version: str
    duration_ms: int
    attempts: int
    policy_decision: dict[str, Any]


class InvokeResponse(BaseModel):
    execution_id: str
    trace_id: str
    status: Literal["succeeded"]
    data: dict[str, Any]
    error: None = None
    meta: InvokeMeta


class ExecutionRead(BaseModel):
    id: str
    trace_id: str
    status: str
    agent_id: str
    agent_name: str
    principal_id: str | None
    principal_name: str | None
    tool_id: str
    tool_name: str
    tool_version: str
    request_source: str
    error_code: str | None
    error_message_safe: str | None
    started_at: datetime
    finished_at: datetime | None
    duration_ms: int | None
    attempts: int
    policy_decision: dict[str, Any] | None
