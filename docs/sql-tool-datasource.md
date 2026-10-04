# SQL Tool 只读数据源接入

Phase 2 将平台元数据库连接和 Agent 可查询的数据源连接视为两个安全边界：

- `DATABASE_URL`：平台保存 Agent、Tool、权限、Execution 和 Audit 的连接；
- `SQL_TOOL_DATABASE_URL`：三个 SQL Tool 使用的独立只读身份连接。

当前演示环境可以共用同一个 Neon 数据库，但必须使用独立角色，并将业务数据放在专用的 `tool_data` Schema 中。不要向只读角色授予平台 `public` Schema 中元数据表的读取权限。

## 1. 创建角色与专用 Schema

优先在 Neon 的 Roles 页面创建 `agent_tool_reader`，由 Neon 生成并保存密码。然后在 SQL Editor 中选择 `production`、`neondb` 和 `neondb_owner`，执行：

```sql
CREATE SCHEMA IF NOT EXISTS tool_data
AUTHORIZATION neondb_owner;

GRANT CONNECT ON DATABASE neondb
TO agent_tool_reader;

GRANT USAGE ON SCHEMA tool_data
TO agent_tool_reader;

GRANT SELECT ON ALL TABLES IN SCHEMA tool_data
TO agent_tool_reader;

ALTER DEFAULT PRIVILEGES
FOR ROLE neondb_owner
IN SCHEMA tool_data
GRANT SELECT ON TABLES TO agent_tool_reader;
```

Neon 管理的角色可能不允许 `neondb_owner` 执行 `ALTER ROLE agent_tool_reader SET ...`。这不影响平台：SQL Tool 会在每个事务中强制 `READ ONLY`、`statement_timeout` 和 `search_path`，并在执行前解析和拒绝写 SQL。

`ALTER DEFAULT PRIVILEGES` 只影响以后由 `neondb_owner` 创建的表。如果将来使用另一个 Owner 创建业务表，需要为该 Owner 再执行一次对应语句。

## 2. 验证数据库权限

```sql
SELECT
    has_database_privilege('agent_tool_reader', 'neondb', 'CONNECT') AS can_connect,
    has_schema_privilege('agent_tool_reader', 'tool_data', 'USAGE') AS can_use_schema,
    has_schema_privilege('agent_tool_reader', 'tool_data', 'CREATE') AS can_create_objects;
```

预期 `can_connect` 和 `can_use_schema` 为 `true`，`can_create_objects` 为 `false`。

## 3. 配置独立连接串

在 Neon Connect 界面选择：

- Branch：`production`
- Compute：`Primary`
- Database：`neondb`
- Role：`agent_tool_reader`
- Connection pooling：开启

将复制的完整连接串写入本地 `.env`：

```dotenv
SQL_TOOL_DATABASE_URL=postgresql://agent_tool_reader:<password>@<pooler-host>/neondb?sslmode=require
SQL_TOOL_ALLOWED_SCHEMAS=["tool_data"]
SQL_TOOL_STATEMENT_TIMEOUT_MS=5000
SQL_TOOL_DEFAULT_MAX_ROWS=100
SQL_TOOL_ABSOLUTE_MAX_ROWS=1000
```

不要替换 `DATABASE_URL`，不要提交 `.env`，也不要在日志或文档中保存真实密码。

## 4. 验证平台链路

重启 `scripts/dev.ps1` 后：

1. 请求 `http://127.0.0.1:8000/api/v1/sql-datasource/status`，确认 `configured` 和 `safely_separated` 均为 `true`；
2. 在 Tools 页面用 Local Analyst 调用 `sql.list_tables`，参数为 `{"schema":"tool_data"}`；
3. 调用 `sql.query_readonly` 执行 `SELECT 1 AS value`；
4. 用 Local Viewer 调用相同 Tool，应得到 `PERMISSION_DENIED`；
5. 尝试 `CREATE`、`UPDATE` 或多语句 SQL，应在执行前被拒绝；
6. 在 Executions 和 Audit 页面确认 allowed、denied 和 error 记录。

如果没有配置 `SQL_TOOL_DATABASE_URL`，平台会安全关闭 SQL 执行并返回 `DATASOURCE_UNAVAILABLE`，其余 Agent/Tool 目录、RBAC、审计和 `system.echo` 仍可使用。
