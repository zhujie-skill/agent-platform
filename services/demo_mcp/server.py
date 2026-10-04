from __future__ import annotations

import os
from datetime import UTC, datetime

from mcp.server import MCPServer

mcp = MCPServer(
    "Demo Market Data",
    instructions="Deterministic market data tools for the Agent Tool Platform demo.",
)


@mcp.tool()
def market_snapshot(symbol: str) -> dict[str, str | float]:
    """Return a deterministic demo quote for a stock symbol."""
    normalized = symbol.strip().upper()
    prices = {"AAPL": 227.16, "MSFT": 417.79, "NVDA": 121.40}
    return {
        "symbol": normalized,
        "price": prices.get(normalized, 100.0),
        "currency": "USD",
        "as_of": datetime.now(UTC).isoformat(),
        "source": "phase3-demo-mcp",
    }


if __name__ == "__main__":
    mcp.run(
        transport="streamable-http",
        host=os.getenv("DEMO_MCP_HOST", "127.0.0.1"),
        port=int(os.getenv("DEMO_MCP_PORT", "8101")),
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )
