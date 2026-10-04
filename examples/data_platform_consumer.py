"""Phase 4 handoff example: a future Data Agent consuming governed SQL Tools."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "packages" / "python-sdk" / "src"))

from agent_platform_sdk import AgentPlatformClient

DATA_AGENT_ID = os.getenv(
    "DATA_AGENT_ID", "00000000-0000-0000-0000-000000000101"
)
PLATFORM_URL = os.getenv("AGENT_PLATFORM_URL", "http://127.0.0.1:8000")
SERVICE_ACCOUNT = os.getenv("AGENT_PLATFORM_PRINCIPAL", "data-agent-runtime")


def main() -> None:
    with AgentPlatformClient(
        PLATFORM_URL, principal=SERVICE_ACCOUNT
    ) as platform:
        compatibility = platform.compatibility()
        tools = platform.list_available_tools(DATA_AGENT_ID)
        sql_tools = sorted(tool.name for tool in tools if tool.name.startswith("sql."))
        print(f"API {compatibility['api_family']} SQL Tools: {', '.join(sql_tools)}")

        catalog = platform.invoke(
            "sql.list_tables",
            agent_id=DATA_AGENT_ID,
            arguments={"schema": "tool_data"},
            request_source="data-platform-example",
        )
        print("Tables:", catalog.data["tables"], "trace:", catalog.trace_id)

        result = platform.invoke(
            "sql.query_readonly",
            agent_id=DATA_AGENT_ID,
            arguments={
                "query": (
                    "SELECT symbol, price, currency FROM tool_data.market_prices "
                    "ORDER BY symbol"
                ),
                "max_rows": 20,
            },
            request_source="data-platform-example",
        )
        print("Rows:", result.data["rows"], "trace:", result.trace_id)


if __name__ == "__main__":
    main()
