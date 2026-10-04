import httpx
import pytest

from agent_platform_sdk import AgentPlatformClient, AgentPlatformError

DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"


def test_discovery_and_invoke_use_service_account_contract() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["X-Local-Principal"] == "data-agent-runtime"
        if request.url.path.endswith("/available-tools"):
            return httpx.Response(
                200,
                json=[
                    {
                        "id": "tool-id",
                        "name": "sql.list_tables",
                        "title": "List Tables",
                        "description": "List allowed tables",
                        "input_schema": {"type": "object"},
                        "version": "1.0.0",
                        "provider_type": "native",
                        "risk_level": "low",
                    }
                ],
            )
        assert request.url.path == "/api/v1/tools/sql/list_tables:invoke"
        payload = __import__("json").loads(request.content)
        assert payload["context"]["agent_id"] == DATA_AGENT_ID
        return httpx.Response(
            200,
            json={
                "execution_id": "execution-id",
                "trace_id": "trace-id",
                "status": "succeeded",
                "data": {"schema": "tool_data", "tables": []},
                "error": None,
                "meta": {"version": "1.0.0"},
            },
        )

    with AgentPlatformClient(
        principal="data-agent-runtime", transport=httpx.MockTransport(handler)
    ) as client:
        tools = client.list_available_tools(DATA_AGENT_ID)
        result = client.invoke(
            tools[0].name,
            agent_id=DATA_AGENT_ID,
            arguments={"schema": "tool_data"},
        )
    assert tools[0].version == "1.0.0"
    assert result.trace_id == "trace-id"


def test_structured_platform_error_is_preserved() -> None:
    transport = httpx.MockTransport(
        lambda _request: httpx.Response(
            403,
            json={
                "detail": {
                    "code": "AGENT_SCOPE_DENIED",
                    "message": "Wrong Agent.",
                }
            },
        )
    )
    with (
        AgentPlatformClient(principal="data-agent-runtime", transport=transport) as client,
        pytest.raises(AgentPlatformError) as caught,
    ):
        client.list_available_tools("another-agent")
    assert caught.value.code == "AGENT_SCOPE_DENIED"
    assert caught.value.status_code == 403
