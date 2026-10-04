# Agent Tool Platform

面向量化团队的 Agent 平台 + Tool 平台。当前完成 Phase 4：在完整工具中台之上，固化了未来数据中台使用的 SQL Tool、service account、Python SDK 和 API v1 兼容边界。

完整范围与长期路线见 [plan.md](./plan.md)，架构图见 [docs/architecture/overview.md](./docs/architecture/overview.md)。

## 当前能力

- Agent Catalog：Data、Developer、Operations、Security Agent；
- Tool Registry：数据库为运行时权威来源，不使用 Manifest 隐式同步；
- Native Tool：本仓库实现，数据库保存不可变版本和 handler key；
- HTTP Tool：配置键间接寻址、origin allowlist、超时、响应大小限制；
- 外部 MCP：Server 登记 → 显式 discovery → schema 快照 → 显式导入与绑定；
- 平台 MCP facade：标准 MCP Client 只能发现指定 Agent/Principal 获授权的 Tool；
- 治理：本地身份、RBAC、风险策略、只读 SQL、脱敏、Execution 与 Audit；
- 演示：指标卡片、Docker Compose、确定性数据和一键配置脚本。
- 数据中台交接：Agent-scoped service account、Python SDK、稳定 SQL 契约和接入示例。

## 技术栈与目录

- Control Plane：Next.js 16、React、TypeScript
- Control API / Tool Gateway：FastAPI、Python
- MCP：官方 Python SDK、Streamable HTTP
- 持久化：云 PostgreSQL、SQLAlchemy、Alembic

```text
apps/web/                 Control Plane
apps/api/                 Control API、Gateway、Executors
services/platform_mcp/    本平台对外 MCP facade
services/demo_mcp/        外部 MCP 演示服务
migrations/               版本化数据库结构与基础目录
scripts/                  Windows 初始化、迁移、启动、验收脚本
docs/                     架构、ADR、演示与排障
packages/python-sdk/      Agent runtime 使用的 Python SDK
examples/                 跨中台消费示例
```

## 本地快速开始

要求 Node.js 22+、Corepack、Python 3.11+。应用仅在本机运行，元数据和演示数据持久化到云 PostgreSQL。

```powershell
.\scripts\setup.ps1
```

在 `.env` 填入 `DATABASE_URL`；SQL Tool 还需填入权限受限的 `SQL_TOOL_DATABASE_URL`。连接串只保存在已忽略的 `.env`，不要提交。随后执行：

```powershell
.\scripts\db-migrate.ps1
.\scripts\dev.ps1
```

`dev.ps1` 同时启动：

| 服务 | 地址 | 作用 |
|---|---|---|
| Control Plane | http://localhost:3000 | 可视化治理 |
| Control API | http://127.0.0.1:8000/docs | Registry 与统一 Gateway |
| Platform MCP | http://127.0.0.1:8100/mcp | 向 MCP Client 暴露获授权 Tool |
| Demo MCP | http://127.0.0.1:8101/mcp | 模拟外部 `market_snapshot` |

保持服务运行，再开一个 PowerShell：

```powershell
.\scripts\seed-demo.ps1
```

该脚本幂等写入三条 `tool_data.market_prices`，登记 Demo MCP Server，执行 discovery，导入 `external.market-snapshot`，并绑定给 Data Agent。完整 8 分钟演示流程见 [docs/demo.md](./docs/demo.md)。

## 手动验收 Phase 3

1. 打开 Overview，确认 Agents、Active Tools、24h success 和 Providers 有值。
2. 打开 MCP，确认 `demo-market` 为 `healthy`，`market_snapshot` 为 `unchanged`。
3. 打开 Tools，用 Data Agent 调用 `external.market-snapshot`，参数为 `{"symbol":"AAPL"}`。
4. 用 Operations Agent 调用 `http.health_check`，确认仍走同一个 invoke API。
5. 在 Executions 确认 Native、HTTP、MCP 三类调用都有统一 execution/trace/policy 记录。
6. 使用 `scripts/verify_phase3.py` 验证标准 MCP Client 能发现并调用平台 Tool。

```powershell
.\.venv\Scripts\python.exe .\scripts\verify_phase3.py
```

## 验收 Phase 4 数据中台交接

迁移到 `0005` 后，运行：

```powershell
.\.venv\Scripts\python.exe .\examples\data_platform_consumer.py
.\.venv\Scripts\python.exe .\scripts\verify_phase4.py
```

该示例使用 `data-agent-runtime` service account 发现 Data Agent 的 SQL Tool，并通过 Gateway 查询演示数据。它无法代表其他 Agent。接入边界见 [数据中台交接](./docs/data-platform-handoff.md)，稳定 SQL 契约见 [SQL Tool Contract v1](./docs/contracts/sql-tools-v1.md)，兼容性承诺见 [API v1 兼容性](./docs/contracts/api-compatibility.md)。机器可读契约位于 `GET /api/v1/compatibility`。

## 自动检查

```powershell
.\scripts\check.ps1
```

包括 Ruff、API tests、TypeScript 类型检查和 Next.js 生产构建。

## Docker Compose（可选演示模式）

Compose 不创建本地数据库，仍读取 `.env` 中的云数据库连接：

```powershell
docker compose up --build
docker compose exec api alembic upgrade head
```

容器内 MCP 地址与本机地址不同；`compose.yaml` 已通过环境变量覆盖 allowlist。首次导入时在 MCP 页面使用 `http://demo-mcp:8101/mcp`。

## 数据库与安全边界

- `DATABASE_URL` 是平台元数据管理连接；
- `SQL_TOOL_DATABASE_URL` 必须是独立只读角色，不能与前者相同；
- SQL Executor 还限制 schema、只读事务、单语句、statement timeout 和最大行数；
- HTTP 与 MCP endpoint 都是 exact allowlist，禁止运行时任意 URL；
- MCP 密钥只保存 `env:VARIABLE` 引用，不保存明文；
- 当前身份提供者是本地演示实现，不可直接用于生产。

只读角色配置见 [docs/sql-tool-datasource.md](./docs/sql-tool-datasource.md)，常见问题见 [docs/troubleshooting.md](./docs/troubleshooting.md)。
