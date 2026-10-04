from fastapi import APIRouter

from app.schemas.compatibility import CompatibilityRead, ContractReference

router = APIRouter(tags=["compatibility"])


@router.get("/compatibility", response_model=CompatibilityRead)
def compatibility() -> CompatibilityRead:
    """Machine-readable handoff contract for future Agent runtimes."""
    return CompatibilityRead(
        api_family="v1",
        status="stable",
        discovery_endpoint="/api/v1/agents/{agent_id}/available-tools",
        invoke_endpoint_template="/api/v1/tools/{namespace}/{name}:invoke",
        identity_header="X-Local-Principal",
        minimum_python_sdk_version="0.1.0",
        contracts={
            name: ContractReference(
                version="1.0.0",
                stability="stable",
                documentation="/docs/contracts/sql-tools-v1.md",
            )
            for name in (
                "sql.list_tables",
                "sql.describe_table",
                "sql.query_readonly",
            )
        },
        guarantees=[
            "Published Tool versions are immutable.",
            "Additive response fields may appear within API v1.",
            "Removing or changing a field requires a new Tool or API version.",
            "Every accepted invocation returns execution_id and trace_id.",
            "Every denied or completed invocation emits an audit event.",
        ],
    )
