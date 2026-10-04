import pytest
from fastapi.testclient import TestClient

from app.core.config import get_settings
from app.runtime.errors import ToolRuntimeError
from app.runtime.sql_tools import default_allowed_schema
from tests.conftest import DATA_AGENT_ID, DEVELOPER_AGENT_ID


def test_service_account_is_visible_and_scoped(api_client: TestClient) -> None:
    principals = api_client.get("/api/v1/principals").json()
    service_account = next(
        item for item in principals if item["external_id"] == "data-agent-runtime"
    )
    assert service_account["type"] == "service_account"
    assert service_account["agent_id"] == DATA_AGENT_ID
    assert service_account["agent_name"] == "platform.data-agent"
    assert service_account["permissions"] == ["database.read", "tool.invoke"]

    allowed = api_client.get(
        f"/api/v1/agents/{DATA_AGENT_ID}/available-tools",
        headers={"X-Local-Principal": "data-agent-runtime"},
    )
    denied = api_client.get(
        f"/api/v1/agents/{DEVELOPER_AGENT_ID}/available-tools",
        headers={"X-Local-Principal": "data-agent-runtime"},
    )
    assert allowed.status_code == 200
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "AGENT_SCOPE_DENIED"


def test_service_account_cannot_invoke_for_another_agent(
    api_client: TestClient,
) -> None:
    response = api_client.post(
        "/api/v1/tools/system/echo:invoke",
        headers={"X-Local-Principal": "data-agent-runtime"},
        json={
            "arguments": {"message": "must be denied"},
            "context": {"agent_id": DEVELOPER_AGENT_ID},
        },
    )
    assert response.status_code == 403
    assert response.json()["detail"]["code"] == "AGENT_SCOPE_DENIED"
    audit = api_client.get("/api/v1/audit-events").json()[0]
    assert audit["decision"] == "denied"
    assert audit["metadata_redacted"]["error_code"] == "AGENT_SCOPE_DENIED"


def test_machine_readable_compatibility_contract(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/compatibility")
    assert response.status_code == 200
    payload = response.json()
    assert payload["api_family"] == "v1"
    assert payload["contracts"]["sql.query_readonly"]["version"] == "1.0.0"
    assert "{namespace}" in payload["invoke_endpoint_template"]


def test_default_sql_schema_uses_first_allowlisted_schema(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    settings = get_settings()
    monkeypatch.setattr(settings, "sql_tool_allowed_schemas", ["tool_data"])
    assert default_allowed_schema() == "tool_data"
    monkeypatch.setattr(settings, "sql_tool_allowed_schemas", [])
    with pytest.raises(ToolRuntimeError) as caught:
        default_allowed_schema()
    assert caught.value.code == "SCHEMA_NOT_ALLOWED"
