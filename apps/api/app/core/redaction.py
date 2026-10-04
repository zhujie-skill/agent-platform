from hashlib import sha256
from typing import Any

SENSITIVE_KEY_PARTS = (
    "password",
    "passwd",
    "secret",
    "token",
    "api_key",
    "apikey",
    "authorization",
    "connection_string",
    "database_url",
    "dsn",
    "ssn",
)


def is_sensitive_key(key: str) -> bool:
    normalized = key.lower()
    return any(part in normalized for part in SENSITIVE_KEY_PARTS)


def redact_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {
            str(key): "***REDACTED***" if is_sensitive_key(str(key)) else redact_value(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_value(item) for item in value]
    return value


def redact_arguments(handler_key: str, arguments: dict[str, Any]) -> dict[str, Any]:
    redacted = redact_value(arguments)
    if handler_key == "sql.query_readonly" and isinstance(arguments.get("query"), str):
        query = arguments["query"]
        redacted["query"] = {
            "sha256": sha256(query.encode()).hexdigest(),
            "character_count": len(query),
            "content": "***SQL_TEXT_REDACTED***",
        }
    return redacted


def redact_result(handler_key: str, result: dict[str, Any]) -> dict[str, Any]:
    if handler_key == "sql.query_readonly":
        return {
            "columns": result.get("columns", []),
            "row_count": result.get("row_count", 0),
            "truncated": result.get("truncated", False),
            "rows": "***ROWS_NOT_PERSISTED***",
        }
    return redact_value(result)
