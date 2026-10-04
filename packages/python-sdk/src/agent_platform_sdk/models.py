from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class ToolDefinition:
    id: str
    name: str
    title: str
    description: str
    input_schema: dict[str, Any]
    version: str
    provider_type: str
    risk_level: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "ToolDefinition":
        return cls(**payload)


@dataclass(frozen=True)
class InvocationResult:
    execution_id: str
    trace_id: str
    status: str
    data: dict[str, Any]
    meta: dict[str, Any]

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "InvocationResult":
        return cls(
            execution_id=payload["execution_id"],
            trace_id=payload["trace_id"],
            status=payload["status"],
            data=payload["data"],
            meta=payload["meta"],
        )
