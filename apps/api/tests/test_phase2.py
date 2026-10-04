import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.core.redaction import redact_arguments, redact_result
from app.runtime.errors import ToolRuntimeError
from app.runtime.sql_tools import validate_readonly_query
from tests.conftest import DATA_AGENT_ID


def register_sql_query_tool(api_client: TestClient) -> str:
    registered = api_client.post(
        "/api/v1/tools",
        json={
            "namespace": "sql",
            "name": "query_readonly",
            "display_name": "Read-only SQL Query",
            "description": "Execute one governed read-only query.",
            "owner": "Tool Platform",
            "risk_level": "medium",
            "version": {
                "version": "1.0.0",
                "input_schema": {
                    "type": "object",
                    "required": ["query"],
                    "properties": {"query": {"type": "string"}},
                },
                "output_schema": {"type": "object"},
                "handler_key": "sql.query_readonly",
                "required_permissions": ["database.read"],
                "retry_policy": {"max_attempts": 2, "retry_safe": True},
            },
        },
    )
    assert registered.status_code == 201
    tool_id = registered.json()["id"]
    bound = api_client.put(
        f"/api/v1/agents/{DATA_AGENT_ID}/tools/{tool_id}",
        json={"version_policy": "default", "enabled": True},
    )
    assert bound.status_code == 200
    return tool_id


def test_governance_catalog_exposes_roles_and_permissions(api_client: TestClient) -> None:
    principals = api_client.get("/api/v1/principals")
    roles = api_client.get("/api/v1/roles")
    permissions = api_client.get("/api/v1/permissions")

    assert principals.status_code == roles.status_code == permissions.status_code == 200
    assert {item["external_id"] for item in principals.json()} == {
        "local-admin",
        "local-analyst",
        "local-viewer",
        "data-agent-runtime",
    }
    viewer = next(item for item in principals.json() if item["external_id"] == "local-viewer")
    assert viewer["permissions"] == ["tool.invoke"]


def test_permission_denial_is_persisted_and_audited(api_client: TestClient) -> None:
    register_sql_query_tool(api_client)
    denied = api_client.post(
        "/api/v1/tools/sql/query_readonly:invoke",
        headers={"X-Local-Principal": "local-viewer"},
        json={
            "arguments": {"query": "SELECT 1"},
            "context": {"agent_id": DATA_AGENT_ID, "request_source": "test"},
        },
    )

    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "PERMISSION_DENIED"
    execution = api_client.get("/api/v1/executions").json()[0]
    assert execution["status"] == "denied"
    assert execution["principal_name"] == "Local Viewer"
    assert execution["policy_decision"]["missing_permissions"] == ["database.read"]
    audit = api_client.get("/api/v1/audit-events").json()[0]
    assert audit["decision"] == "denied"
    assert audit["metadata_redacted"]["missing_permissions"] == ["database.read"]


def test_authorized_sql_call_fails_closed_without_separate_datasource(
    api_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "sql_tool_database_url", None)
    register_sql_query_tool(api_client)
    response = api_client.post(
        "/api/v1/tools/sql/query_readonly:invoke",
        headers={"X-Local-Principal": "local-analyst"},
        json={
            "arguments": {"query": "SELECT 1"},
            "context": {"agent_id": DATA_AGENT_ID},
        },
    )

    assert response.status_code == 503
    assert response.json()["detail"]["code"] == "DATASOURCE_UNAVAILABLE"
    execution = api_client.get("/api/v1/executions").json()[0]
    assert execution["status"] == "failed"
    assert execution["principal_name"] == "Local Data Analyst"


@pytest.mark.parametrize(
    "query",
    [
        "UPDATE orders SET status = 'filled'",
        "SELECT 1; SELECT 2",
        "SELECT pg_sleep(1)",
        "SELECT nextval('orders_id_seq')",
        "SELECT pg_advisory_lock(1)",
        "SELECT * FROM private.secrets",
        "SELECT * FROM orders FOR UPDATE",
    ],
)
def test_readonly_sql_validator_rejects_unsafe_queries(query: str) -> None:
    with pytest.raises(ToolRuntimeError):
        validate_readonly_query(query)


def test_readonly_sql_validator_accepts_select_and_cte() -> None:
    assert validate_readonly_query("SELECT 1 AS value").startswith("SELECT")
    assert validate_readonly_query("WITH x AS (SELECT 1) SELECT * FROM x").startswith("WITH")


def test_redaction_does_not_persist_sql_text_or_rows() -> None:
    arguments = redact_arguments(
        "sql.query_readonly", {"query": "SELECT * FROM accounts WHERE id = 42", "max_rows": 10}
    )
    result = redact_result(
        "sql.query_readonly",
        {"columns": ["id"], "rows": [{"id": 42}], "row_count": 1, "truncated": False},
    )

    assert arguments["query"]["content"] == "***SQL_TEXT_REDACTED***"
    assert "accounts" not in str(arguments)
    assert result["rows"] == "***ROWS_NOT_PERSISTED***"
