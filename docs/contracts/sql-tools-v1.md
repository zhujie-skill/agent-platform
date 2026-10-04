# SQL Tool Contract v1

状态：`stable`。消费方通过 Agent discovery 获取实际 JSON Schema，不应在代码中复制 schema。

## `sql.list_tables` 1.0.0

输入：可选 `schema: string`。建议消费方始终显式传入；省略时使用部署配置中第一个允许的 schema。

输出：`schema` 和按名称排序的 `tables[]`；每项包含 `name` 与 `type`（`table` 或 `view`）。

## `sql.describe_table` 1.0.0

输入：必填 `table`，可选 `schema`。表名和 schema 必须是安全标识符，schema 必须位于 allowlist。

输出：`schema`、`table`、`columns[]`；列包含 `name`、`data_type`、`nullable`。

## `sql.query_readonly` 1.0.0

输入：必填 `query`，可选 `max_rows`。仅接受单条 PostgreSQL `SELECT` 或 `WITH` 查询。

输出：`columns[]`、`rows[]`、`row_count`、`truncated`。服务端会取 `max_rows + 1` 判断截断，但只返回上限内的行。

## 共同错误

错误使用 HTTP 状态和 `{ "detail": { "code", "message" } }`：

- `PERMISSION_DENIED`：身份缺少 `database.read`；
- `AGENT_SCOPE_DENIED`：service account 尝试代表其他 Agent；
- `TOOL_NOT_BOUND`：Agent 未绑定 Tool；
- `SCHEMA_NOT_ALLOWED`：schema 不在 allowlist；
- `SQL_NOT_READ_ONLY`、`SQL_FUNCTION_DENIED`：查询违反只读规则；
- `DATASOURCE_UNAVAILABLE`、`SQL_EXECUTION_FAILED`：数据源不可用或执行失败。

成功调用一定包含 `execution_id`、`trace_id`、解析后的 Tool 版本和 policy decision。SQL 文本与结果行不会原样写入 Execution/Audit。
