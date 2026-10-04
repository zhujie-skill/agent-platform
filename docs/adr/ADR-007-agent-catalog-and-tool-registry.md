# ADR-007：Agent Catalog、统一 Tool Registry 与多对多复用

- 状态：Accepted
- 日期：2026-10-02
- 替代：[ADR-006：数据库通用工具与代码内本地工具分离](./ADR-006-shared-and-local-tools.md)

## 背景

本项目面向用户呈现的不是单独的工具目录，而是一个同时包含 Agent 与 Tool 的平台。用户能看到数据、研发、运维、安全等 Agent，也能看到 Git、数据库、日志和外部 MCP 等 Tool。同一个 Tool 可能被多个 Agent 调用，因此复用关系本身就是平台需要管理的一等数据。

此前将 Tool 分成“数据库中的通用工具”和“代码内的项目本地工具”，会造成两个发现与调用入口，也无法完整表达平台原生 Tool 应被多个 Agent 复用的目标。

## 决策

1. 建立用户可见的 Agent Catalog 与 Tool Catalog。
2. 所有需要被 Agent 发现和调用的 Tool 都必须登记在中央 Tool Registry；数据库是 Tool 定义、版本、状态和执行路由的运行时权威来源。
3. Tool 实现来源分为 `native` 与 `mcp`：
   - 平台原生 Tool 的实现代码位于本仓库，Registry 通过受控 `handler_key` 路由；
   - 外部 MCP Tool 的实现位于外部 MCP Server，Registry 保存显式导入的定义快照和远端路由。
4. Agent 与 Tool 通过数据库中的多对多绑定管理。一个 Agent 可以使用多个 Tool，一个 Tool 可以被多个 Agent 复用。
5. Agent Runtime 只获得已绑定、已启用、版本可用且通过权限策略的 Tool。
6. 不使用本地 Manifest 与 Registry 的隐式同步。MCP 发现、导入和刷新是显式、可审计的操作。
7. 不需要被 Agent 发现或调用的内部辅助函数只是应用代码，不属于 Tool，不建立第二套本地 Tool Registry。

## 结果

- Agent 页面可以解释“这个 Agent 能使用什么”；Tool 页面可以解释“这个 Tool 被谁复用”；
- 平台原生 Tool 与外部 MCP Tool 共享目录、绑定、权限、版本、调用和审计链路；
- Git、数据库等能力只需要定义和实现一次，即可绑定给多个中台 Agent；
- 数据库不保存可执行源代码，代码部署与 Tool 发布仍是两个明确步骤；
- 原生代码与 Registry 契约需要通过发布校验和契约测试防止漂移；
- 外部 MCP Schema 变化不会静默覆盖已发布版本。

## 备选方案

曾考虑保留代码内 `LocalToolRegistry`。它适合普通应用的插件机制，但会形成 Agent 无法从统一目录发现、平台无法统一授权和审计的旁路，因此不采用。

也考虑过把原生 Tool 源代码存入数据库。该方案增加动态代码执行风险，且不利于代码审查、测试和部署，因此数据库只保存契约与路由。

## 重新评估条件

如果未来需要 GitOps 或多环境声明式发布，可以为 Registry 增加签名制品、导入/导出和审批流程；除非另立 ADR，否则不得引入两个并行的运行时 Tool 目录，也不得绕过 Agent—Tool 绑定和统一 Gateway。
