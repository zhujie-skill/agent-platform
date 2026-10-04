from fastapi.testclient import TestClient

from tests.conftest import DATA_AGENT_ID, ECHO_TOOL_ID


def test_catalog_exposes_reusable_tool(api_client: TestClient) -> None:
    agents = api_client.get("/api/v1/agents")
    tools = api_client.get("/api/v1/tools")

    assert agents.status_code == 200
    assert tools.status_code == 200
    assert len(agents.json()) == 2
    assert all(agent["tools"][0]["name"] == "echo" for agent in agents.json())
    assert len(tools.json()[0]["consumer_agents"]) == 2


def test_bound_agent_can_invoke_echo_and_create_execution(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/tools/system/echo:invoke",
        json={
            "arguments": {"message": "phase one works"},
            "context": {"agent_id": DATA_AGENT_ID, "request_source": "test"},
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["data"] == {"message": "phase one works"}
    assert payload["meta"]["tool"] == "system.echo"
    assert payload["execution_id"]
    assert payload["trace_id"]

    executions = api_client.get("/api/v1/executions").json()
    assert len(executions) == 1
    assert executions[0]["status"] == "succeeded"
    assert executions[0]["agent_name"] == "Data Agent"


def test_invalid_input_is_structured_and_recorded(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/tools/system/echo:invoke",
        json={"arguments": {}, "context": {"agent_id": DATA_AGENT_ID}},
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "INPUT_VALIDATION_FAILED"
    executions = api_client.get("/api/v1/executions").json()
    assert executions[0]["status"] == "failed"
    assert executions[0]["error_code"] == "INPUT_VALIDATION_FAILED"


def test_unbound_agent_is_denied_until_binding_is_created(api_client: TestClient) -> None:
    created = api_client.post(
        "/api/v1/agents",
        json={
            "namespace": "platform",
            "name": "security-agent",
            "display_name": "Security Agent",
            "description": "Security consumer",
            "agent_type": "security",
            "owner": "Security Platform",
        },
    )
    assert created.status_code == 201
    agent_id = created.json()["id"]

    denied = api_client.post(
        "/api/v1/tools/system/echo:invoke",
        json={"arguments": {"message": "hello"}, "context": {"agent_id": agent_id}},
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "TOOL_NOT_BOUND"

    bound = api_client.put(
        f"/api/v1/agents/{agent_id}/tools/{ECHO_TOOL_ID}",
        json={"version_policy": "default", "enabled": True},
    )
    assert bound.status_code == 200
    assert len(bound.json()["tools"]) == 1

    allowed = api_client.post(
        "/api/v1/tools/system/echo:invoke",
        json={"arguments": {"message": "hello"}, "context": {"agent_id": agent_id}},
    )
    assert allowed.status_code == 200


def test_published_version_is_immutable(api_client: TestClient) -> None:
    duplicate = api_client.post(
        f"/api/v1/tools/{ECHO_TOOL_ID}/versions",
        json={
            "version": "1.0.0",
            "input_schema": {"type": "object"},
            "output_schema": {"type": "object"},
            "handler_key": "system.echo",
        },
    )

    assert duplicate.status_code == 409
    assert duplicate.json()["detail"]["code"] == "TOOL_VERSION_ALREADY_EXISTS"


def test_unbinding_preserves_execution_history(api_client: TestClient) -> None:
    invoked = api_client.post(
        "/api/v1/tools/system/echo:invoke",
        json={
            "arguments": {"message": "keep history"},
            "context": {"agent_id": DATA_AGENT_ID},
        },
    )
    assert invoked.status_code == 200

    unbound = api_client.delete(f"/api/v1/agents/{DATA_AGENT_ID}/tools/{ECHO_TOOL_ID}")
    assert unbound.status_code == 204
    assert len(api_client.get("/api/v1/executions").json()) == 1

    denied = api_client.post(
        "/api/v1/tools/system/echo:invoke",
        json={
            "arguments": {"message": "no longer allowed"},
            "context": {"agent_id": DATA_AGENT_ID},
        },
    )
    assert denied.status_code == 403
    assert denied.json()["detail"]["code"] == "TOOL_NOT_BOUND"


def test_registration_rejects_unknown_native_handler(api_client: TestClient) -> None:
    response = api_client.post(
        "/api/v1/tools",
        json={
            "namespace": "system",
            "name": "missing",
            "display_name": "Missing",
            "description": "Should not register",
            "owner": "Tool Platform",
            "version": {
                "version": "1.0.0",
                "input_schema": {"type": "object"},
                "output_schema": {"type": "object"},
                "handler_key": "system.does_not_exist",
            },
        },
    )

    assert response.status_code == 422
    assert response.json()["detail"]["code"] == "NATIVE_HANDLER_NOT_FOUND"
