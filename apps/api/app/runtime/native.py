import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

NativeHandler = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]


async def system_echo(arguments: dict[str, Any]) -> dict[str, Any]:
    return {"message": arguments["message"]}


async def sql_list_tables(arguments: dict[str, Any]) -> dict[str, Any]:
    from app.runtime.sql_tools import list_tables

    return await asyncio.to_thread(list_tables, arguments)


async def sql_describe_table(arguments: dict[str, Any]) -> dict[str, Any]:
    from app.runtime.sql_tools import describe_table

    return await asyncio.to_thread(describe_table, arguments)


async def sql_query_readonly(arguments: dict[str, Any]) -> dict[str, Any]:
    from app.runtime.sql_tools import query_readonly

    return await asyncio.to_thread(query_readonly, arguments)


NATIVE_HANDLERS: dict[str, NativeHandler] = {
    "system.echo": system_echo,
    "sql.list_tables": sql_list_tables,
    "sql.describe_table": sql_describe_table,
    "sql.query_readonly": sql_query_readonly,
}


def has_native_handler(handler_key: str) -> bool:
    return handler_key in NATIVE_HANDLERS


async def execute_native(handler_key: str, arguments: dict[str, Any]) -> dict[str, Any]:
    return await NATIVE_HANDLERS[handler_key](arguments)
