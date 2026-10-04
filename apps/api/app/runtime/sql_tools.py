from __future__ import annotations

import re
from datetime import date, datetime
from decimal import Decimal
from functools import lru_cache
from typing import Any
from uuid import UUID

import sqlglot
from sqlalchemy import Engine, create_engine, inspect, text
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlglot import exp
from sqlglot.errors import ParseError

from app.core.config import get_settings
from app.db.session import normalize_database_url
from app.runtime.errors import ToolRuntimeError

SAFE_IDENTIFIER = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
DENIED_FUNCTIONS = {
    "dblink",
    "lo_export",
    "lo_import",
    "nextval",
    "setval",
    "pg_advisory_lock",
    "pg_advisory_xact_lock",
    "pg_read_binary_file",
    "pg_read_file",
    "pg_sleep",
    "pg_terminate_backend",
    "pg_write_file",
}
FORBIDDEN_EXPRESSIONS = tuple(
    expression
    for name in (
        "Alter",
        "Command",
        "Copy",
        "Create",
        "Delete",
        "Drop",
        "Grant",
        "Insert",
        "Into",
        "Lock",
        "Merge",
        "Set",
        "Transaction",
        "Update",
    )
    if (expression := getattr(exp, name, None)) is not None
)
SENSITIVE_COLUMN_PARTS = ("password", "secret", "token", "api_key", "apikey", "ssn")


@lru_cache
def _create_sql_tool_engine(database_url: str) -> Engine:
    settings = get_settings()
    return create_engine(
        normalize_database_url(database_url),
        pool_pre_ping=True,
        pool_recycle=300,
        connect_args={"connect_timeout": settings.database_connect_timeout_seconds},
    )


def get_sql_tool_engine() -> Engine:
    settings = get_settings()
    url = settings.sql_tool_database_url_value
    if url is None:
        raise ToolRuntimeError(
            "DATASOURCE_UNAVAILABLE",
            "SQL_TOOL_DATABASE_URL is not configured. Add a dedicated read-only connection.",
        )
    if settings.database_url_value and normalize_database_url(url) == normalize_database_url(
        settings.database_url_value
    ):
        raise ToolRuntimeError(
            "UNSAFE_DATASOURCE_CONFIGURATION",
            "SQL Tool datasource must not reuse the platform metadata connection.",
        )
    return _create_sql_tool_engine(url)


def allowed_schema(schema: str) -> str:
    settings = get_settings()
    if not SAFE_IDENTIFIER.fullmatch(schema) or schema not in settings.sql_tool_allowed_schemas:
        raise ToolRuntimeError(
            "SCHEMA_NOT_ALLOWED",
            f"Schema '{schema}' is not in the configured allowlist.",
        )
    return schema


def default_allowed_schema() -> str:
    schemas = get_settings().sql_tool_allowed_schemas
    if not schemas:
        raise ToolRuntimeError(
            "SCHEMA_NOT_ALLOWED", "No SQL Tool schema is configured in the allowlist."
        )
    return allowed_schema(schemas[0])


def validate_readonly_query(query: str) -> str:
    try:
        statements = sqlglot.parse(query, read="postgres")
    except ParseError as error:
        raise ToolRuntimeError("SQL_PARSE_FAILED", "SQL could not be parsed safely.") from error
    if len(statements) != 1 or statements[0] is None:
        raise ToolRuntimeError("SQL_MULTIPLE_STATEMENTS", "Exactly one SQL statement is allowed.")
    statement = statements[0]
    if not isinstance(statement, exp.Query):
        raise ToolRuntimeError("SQL_NOT_READ_ONLY", "Only SELECT or WITH queries are allowed.")
    if any(isinstance(node, FORBIDDEN_EXPRESSIONS) for node in statement.walk()):
        raise ToolRuntimeError("SQL_NOT_READ_ONLY", "The query contains a forbidden operation.")
    for function in statement.find_all(exp.Func):
        function_name = str(getattr(function, "name", "") or function.sql_name()).lower()
        if function_name in DENIED_FUNCTIONS:
            raise ToolRuntimeError("SQL_FUNCTION_DENIED", "The query uses a denied function.")
    for table in statement.find_all(exp.Table):
        if table.db and table.db not in get_settings().sql_tool_allowed_schemas:
            raise ToolRuntimeError(
                "SCHEMA_NOT_ALLOWED", f"Schema '{table.db}' is not in the configured allowlist."
            )
    return statement.sql(dialect="postgres")


def serializable(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (date, datetime, Decimal, UUID)):
        return str(value)
    if isinstance(value, bytes):
        return f"<binary:{len(value)} bytes>"
    return str(value)


def redact_sensitive_columns(row: dict[str, Any]) -> dict[str, Any]:
    return {
        key: "***REDACTED***"
        if any(part in key.lower() for part in SENSITIVE_COLUMN_PARTS)
        else serializable(value)
        for key, value in row.items()
    }


def prepare_readonly_connection(connection: Any) -> None:
    settings = get_settings()
    schemas = [allowed_schema(schema) for schema in settings.sql_tool_allowed_schemas]
    quoted_search_path = ", ".join(f'"{schema}"' for schema in schemas)
    connection.execute(text("SET TRANSACTION READ ONLY"))
    connection.execute(
        text(f"SET LOCAL statement_timeout = {settings.sql_tool_statement_timeout_ms}")
    )
    connection.execute(text(f"SET LOCAL search_path TO {quoted_search_path}"))


def list_tables(arguments: dict[str, Any]) -> dict[str, Any]:
    schema = (
        allowed_schema(str(arguments["schema"]))
        if "schema" in arguments
        else default_allowed_schema()
    )
    try:
        with get_sql_tool_engine().connect() as connection, connection.begin():
            prepare_readonly_connection(connection)
            inspector = inspect(connection)
            tables = [
                {"name": name, "type": "table"}
                for name in inspector.get_table_names(schema=schema)
            ] + [
                {"name": name, "type": "view"}
                for name in inspector.get_view_names(schema=schema)
            ]
            return {"schema": schema, "tables": sorted(tables, key=lambda item: item["name"])}
    except ToolRuntimeError:
        raise
    except DBAPIError as error:
        raise ToolRuntimeError(
            "DATASOURCE_UNAVAILABLE", "The read-only datasource is unavailable.", retryable=True
        ) from error
    except SQLAlchemyError as error:
        raise ToolRuntimeError("SQL_TOOL_FAILED", "Unable to list tables safely.") from error


def describe_table(arguments: dict[str, Any]) -> dict[str, Any]:
    schema = (
        allowed_schema(str(arguments["schema"]))
        if "schema" in arguments
        else default_allowed_schema()
    )
    table = str(arguments["table"])
    if not SAFE_IDENTIFIER.fullmatch(table):
        raise ToolRuntimeError("TABLE_NAME_INVALID", "Table name is invalid.")
    try:
        with get_sql_tool_engine().connect() as connection, connection.begin():
            prepare_readonly_connection(connection)
            inspector = inspect(connection)
            if not inspector.has_table(table, schema=schema):
                raise ToolRuntimeError(
                    "TABLE_NOT_FOUND", "Table was not found in an allowed schema."
                )
            columns = [
                {
                    "name": column["name"],
                    "data_type": str(column["type"]),
                    "nullable": bool(column.get("nullable", True)),
                }
                for column in inspector.get_columns(table, schema=schema)
            ]
            return {"schema": schema, "table": table, "columns": columns}
    except ToolRuntimeError:
        raise
    except DBAPIError as error:
        raise ToolRuntimeError(
            "DATASOURCE_UNAVAILABLE", "The read-only datasource is unavailable.", retryable=True
        ) from error
    except SQLAlchemyError as error:
        raise ToolRuntimeError("SQL_TOOL_FAILED", "Unable to describe the table safely.") from error


def query_readonly(arguments: dict[str, Any]) -> dict[str, Any]:
    settings = get_settings()
    canonical_query = validate_readonly_query(str(arguments["query"]))
    requested_rows = int(arguments.get("max_rows", settings.sql_tool_default_max_rows))
    max_rows = min(requested_rows, settings.sql_tool_absolute_max_rows)
    bounded_query = f"SELECT * FROM ({canonical_query}) AS _agent_query LIMIT :_platform_limit"
    try:
        with get_sql_tool_engine().connect() as connection, connection.begin():
            prepare_readonly_connection(connection)
            result = connection.execute(text(bounded_query), {"_platform_limit": max_rows + 1})
            raw_rows = [dict(row) for row in result.mappings().all()]
            truncated = len(raw_rows) > max_rows
            rows = [redact_sensitive_columns(row) for row in raw_rows[:max_rows]]
            return {
                "columns": list(result.keys()),
                "rows": rows,
                "row_count": len(rows),
                "truncated": truncated,
            }
    except ToolRuntimeError:
        raise
    except DBAPIError as error:
        retryable = bool(getattr(error, "connection_invalidated", False))
        raise ToolRuntimeError(
            "SQL_EXECUTION_FAILED",
            "The read-only query could not be completed.",
            retryable=retryable,
        ) from error
    except SQLAlchemyError as error:
        raise ToolRuntimeError(
            "SQL_EXECUTION_FAILED", "The read-only query failed safely."
        ) from error
