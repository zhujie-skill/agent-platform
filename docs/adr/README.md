# Architecture Decision Records

本目录记录影响项目结构、运行方式或长期演进的重要决策。

状态取值：`Proposed`、`Accepted`、`Superseded`、`Deprecated`。

每项决策都应说明背景、决策、结果和重新评估条件。实现改变决策时，应新增 ADR 并将旧 ADR 标记为 `Superseded`，而不是直接覆盖历史原因。

当前记录：

- [ADR-001：Control Plane 与 Execution Plane 分层](./ADR-001-control-and-execution-planes.md)
- [ADR-002：Next.js 与 FastAPI 技术栈](./ADR-002-application-stack.md)
- [ADR-003：云 PostgreSQL 与厂商中立](./ADR-003-cloud-postgresql.md)
- [ADR-004：宿主机优先的本地开发方式](./ADR-004-local-development.md)
- [ADR-005：REST/OpenAPI 核心契约与 MCP 适配层](./ADR-005-protocol-boundary.md)
- [ADR-006：数据库通用工具与代码内本地工具分离（已被替代）](./ADR-006-shared-and-local-tools.md)
- [ADR-007：Agent Catalog、统一 Tool Registry 与多对多复用](./ADR-007-agent-catalog-and-tool-registry.md)

