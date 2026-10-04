from __future__ import annotations

import sys
from pathlib import Path

import psycopg

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "api"))

from app.core.config import get_settings


def main() -> None:
    url = get_settings().database_url_value
    if not url:
        raise SystemExit("DATABASE_URL is not configured in .env")
    with psycopg.connect(url) as connection, connection.cursor() as cursor:
        cursor.execute("CREATE SCHEMA IF NOT EXISTS tool_data")
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS tool_data.market_prices (
                symbol text PRIMARY KEY,
                price numeric(12, 2) NOT NULL,
                currency text NOT NULL,
                observed_at timestamptz NOT NULL DEFAULT now()
            )
            """
        )
        cursor.executemany(
            """
            INSERT INTO tool_data.market_prices (symbol, price, currency)
            VALUES (%s, %s, 'USD')
            ON CONFLICT (symbol) DO UPDATE
            SET price = EXCLUDED.price, currency = EXCLUDED.currency,
                observed_at = now()
            """,
            [("AAPL", 227.16), ("MSFT", 417.79), ("NVDA", 121.40)],
        )
    print("Seeded 3 deterministic rows in tool_data.market_prices.")


if __name__ == "__main__":
    main()
