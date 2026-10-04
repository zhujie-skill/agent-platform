from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.session import get_db_session
from app.models import Agent, Execution, Tool
from app.schemas.metrics import MetricsSummary

router = APIRouter(tags=["metrics"])
SessionDependency = Annotated[Session, Depends(get_db_session)]


@router.get("/metrics/summary", response_model=MetricsSummary)
def metrics_summary(
    session: SessionDependency,
    hours: int = Query(default=24, ge=1, le=24 * 30),
) -> MetricsSummary:
    """Return a small, database-portable operations view for the console."""
    agents = session.scalars(select(Agent)).all()
    tools = session.scalars(select(Tool)).all()
    since = datetime.now(UTC) - timedelta(hours=hours)
    executions = session.scalars(
        select(Execution).where(Execution.started_at >= since)
    ).all()

    statuses = Counter(execution.status for execution in executions)
    finished_durations = [
        execution.duration_ms
        for execution in executions
        if execution.duration_ms is not None
    ]
    succeeded = statuses.get("succeeded", 0)
    failed = sum(
        count for state, count in statuses.items() if state != "succeeded"
    )
    total = len(executions)

    return MetricsSummary(
        window_hours=hours,
        total_agents=len(agents),
        total_tools=len(tools),
        active_tools=sum(tool.status == "active" for tool in tools),
        total_executions=total,
        succeeded_executions=succeeded,
        failed_executions=failed,
        success_rate=round(succeeded / total * 100, 1) if total else 0.0,
        average_duration_ms=(
            round(sum(finished_durations) / len(finished_durations), 1)
            if finished_durations
            else None
        ),
        tools_by_provider=dict(Counter(tool.provider_type for tool in tools)),
        tools_by_risk=dict(Counter(tool.risk_level for tool in tools)),
        executions_by_status=dict(statuses),
    )
