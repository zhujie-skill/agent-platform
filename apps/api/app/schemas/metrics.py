from pydantic import BaseModel


class MetricsSummary(BaseModel):
    window_hours: int
    total_agents: int
    total_tools: int
    active_tools: int
    total_executions: int
    succeeded_executions: int
    failed_executions: int
    success_rate: float
    average_duration_ms: float | None
    tools_by_provider: dict[str, int]
    tools_by_risk: dict[str, int]
    executions_by_status: dict[str, int]
