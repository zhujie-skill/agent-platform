from __future__ import annotations

from agent_platform_sdk import AgentPlatformClient, AgentPlatformError

DATA_AGENT_ID = "00000000-0000-0000-0000-000000000101"
DEVELOPER_AGENT_ID = "00000000-0000-0000-0000-000000000102"


def main() -> None:
    with AgentPlatformClient(principal="data-agent-runtime") as client:
        compatibility = client.compatibility()
        assert compatibility["api_family"] == "v1"
        tools = client.list_available_tools(DATA_AGENT_ID)
        names = {tool.name for tool in tools}
        required = {"sql.list_tables", "sql.describe_table", "sql.query_readonly"}
        assert required <= names

        result = client.invoke(
            "sql.list_tables",
            agent_id=DATA_AGENT_ID,
            arguments={"schema": "tool_data"},
            request_source="phase4-verifier",
        )
        assert any(table["name"] == "market_prices" for table in result.data["tables"])
        print("Data Agent SQL discovery/invoke: succeeded", result.trace_id)

        try:
            client.list_available_tools(DEVELOPER_AGENT_ID)
        except AgentPlatformError as error:
            assert error.code == "AGENT_SCOPE_DENIED"
            print("Cross-Agent service account request: denied as designed")
        else:
            raise AssertionError("Data Agent service account escaped its Agent scope")


if __name__ == "__main__":
    main()
