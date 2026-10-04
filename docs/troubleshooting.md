# 故障排查

## `pnpm` 无法识别

项目脚本通过 Corepack 调用 pnpm。安装 Node.js 22+，重开 PowerShell，运行 `corepack enable` 和 `scripts/setup.ps1`。

## API 显示 database unconfigured / degraded

确认 `.env` 的 `DATABASE_URL` 非空，然后重启 `scripts/dev.ps1`。执行 `scripts/db-migrate.ps1` 后用 `alembic current` 检查版本。

## SQL Tool 返回 DATASOURCE_UNAVAILABLE

确认 `SQL_TOOL_DATABASE_URL` 使用 `agent_tool_reader` 独立角色，并且连接串不等于 `DATABASE_URL`。角色需要 `tool_data` schema 的 USAGE 和表的 SELECT。详情见 `docs/sql-tool-datasource.md`。

## MCP registration 返回 MCP_ENDPOINT_DENIED

endpoint 必须与 `MCP_ALLOWED_ENDPOINTS` 中某一项完全匹配（忽略末尾 `/`）。本机默认是 `http://127.0.0.1:8101/mcp`；Compose 中是 `http://demo-mcp:8101/mcp`。修改 `.env` 后重启 API。

## Discovery 返回 MCP_DISCOVERY_FAILED

先检查 Demo MCP 进程是否监听 8101；再访问 MCP 页面点击 Discover。不要用普通浏览器 GET 判断 Streamable HTTP endpoint 是否正常。

## MCP Tool 显示 changed

远端 input/output schema 与已导入版本的 hash 不同。审查新 schema 后，以新 semver 导入；旧版本不可变。

## Platform MCP 看不到 Tool

Tool 必须 active、有非 deprecated 的解析版本、绑定给 `PLATFORM_AGENT_ID`，且 `PLATFORM_PRINCIPAL` 拥有所需权限。修改环境变量后重启 Platform MCP 服务。

## HTTP Tool 返回 HTTP_ENDPOINT_DENIED

部署 URL 由受控 setting 解析，origin 必须在 `HTTP_TOOL_ALLOWED_ORIGINS`。平台不接受调用参数传入任意 URL。
