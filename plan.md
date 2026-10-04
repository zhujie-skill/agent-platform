# 量化团队 Agent 中台项目规划

> 文档类型：项目 Guide / Architecture Plan  
> 当前阶段：数据中台交接接口（Phase 4 已完成，2026-10-03）  
> 应用运行方式：本地运行，暂不部署  
> 持久化方式：云端托管 PostgreSQL  
> 核心定位：展示完整、清晰、可扩展的工程设计，而非堆叠功能数量

---

## 1. 文档目的

本文档用于定义量化团队 Agent 平台与工具平台的长期方向、当前边界、工具中台架构、开发阶段、技术选型和验收标准。

项目长期规划五个中台：

1. 工具中台（Tool Platform）
2. 数据中台（Data Platform）
3. 研发中台（Developer Platform）
4. 运维中台（Operations Platform）
5. 安全中台（Security Platform）

已经确定的短期开发顺序是：

```text
工具中台 → 数据中台 → 研发中台
```

本版只对共享工具平台进行可实施的详细架构设计，同时定义用户可见的 Agent Catalog 和 Agent—Tool 绑定边界。其余四个中台 Agent 仅说明定位、主要功能和与工具平台的关系，不在本阶段展开各自的内部架构或业务实现。

---

## 2. 项目愿景

这个项目不是为了短期内实现大量 Agent 或大量工具，而是为了展示一套可以逐步成长为团队级 Agent 基础设施的设计。用户感知到的是同一个平台中的两个目录：Agent Catalog 展示数据、研发、运维、安全等 Agent，Tool Catalog 展示这些 Agent 可复用的 Git、数据库、日志、MCP 等工具。

最终，各类 Agent 不应分别处理数据库连接、权限校验、工具发现、超时、重试、日志、审计和执行隔离。它们只负责理解任务、制定计划和选择工具；工具中台负责把工具安全、稳定、可观察地交给 Agent 使用。

长期关系如下。一名 Agent 可以绑定多个 Tool；同一个 Tool 也可以被多个 Agent 复用。

```text
                         用户 / 团队成员
                               │
                    ┌──────────▼──────────┐
                    │    Web Console      │
                    │ Agents  │  Tools    │
                    └────┬────┴────┬──────┘
                         │         │
                 ┌───────▼───┐ ┌──▼──────────┐
                 │Agent       │ │Tool          │
                 │Catalog     │ │Registry      │
                 └───────┬───┘ └──┬──────────┘
                         └────┬────┘
                         Agent—Tool 绑定
                              │
                    ┌─────────▼─────────┐
                    │ Agent Runtime     │
                    │ → Tool Gateway    │
                    └─────────┬─────────┘
                              │
              ┌───────────────┴────────────────┐
              │                                │
      平台原生 Tool 实现                 外部 MCP Tool
      Git / SQL / Logs / ...            MCP Adapter
              │                                │
              └───────────────┬────────────────┘
                              ▼
                        外部系统与资源
```

工具中台是其他中台 Agent 的基础能力提供者，但不承担这些 Agent 的业务决策。例如，工具中台可以提供 `sql.query_readonly`，数据中台 Agent 负责决定何时查询、查询哪张表、如何解释结果。同一个 `sql.query_readonly` 也可以同时绑定给研发 Agent 或安全 Agent，而不复制实现。

---

## 3. 项目范围与非目标

### 3.1 当前范围

当前阶段需要完成：

- 一个可以在本地启动的 Agent 平台 + Tool 平台项目骨架；
- 一个使用 TypeScript 开发的可视化 Control Plane；
- 一个最小 Agent Catalog，以及 Agent 与 Tool 的多对多绑定模型；
- 一个提供统一 API 的 Tool Gateway；
- 工具注册、发现、启停、版本和参数 Schema 管理；
- 一条完整的工具执行链路；
- 基础权限策略、超时、错误处理、执行日志和审计；
- 少量有代表性的示例工具；
- 使用云端 PostgreSQL 保存控制面数据；
- 清晰展示未来如何接入数据、研发、运维和安全中台。

### 3.2 当前非目标

本阶段明确不做：

- 不部署前端、API 或 Tool Worker 到云端；
- 不追求生产级高可用、多地域或自动扩缩容；
- 不实现完整的多租户计费体系；
- 不建设大而全的工作流编排系统；
- 不一次性接入几十种工具；
- 不详细设计另外四个中台；
- 不实现任意 Shell 命令或任意 SQL 的无保护执行；
- 不引入 Kubernetes、Kafka、Service Mesh 等现阶段没有必要的基础设施。

### 3.3 成功标准

项目成功不以“工具数量”衡量，而以以下问题能否得到清晰回答来衡量：

- 新工具如何注册，是否需要修改平台核心代码？
- 用户如何看到 Agent、它能使用哪些 Tool，以及一个 Tool 被哪些 Agent 复用？
- Agent 如何发现工具并取得准确的输入输出 Schema？
- 一次执行经过了哪些组件，失败在哪里？
- 什么身份可以调用什么工具？
- 高风险调用如何被拒绝、审批或记录？
- 工具升级后，已有调用方是否仍可使用旧版本？
- 未来把本地执行迁移为远程 Worker 时，哪些接口无需改变？
- 数据中台和研发中台如何复用这套能力？

---

## 4. 五个中台的长期功能规划

## 4.1 工具中台

工具中台负责统一管理和执行所有可被 Agent 调用的能力，是本阶段唯一进行详细设计和实现的中台。

主要能力：

- Tool Registry：工具注册、发现、分类和版本管理；
- Tool Gateway：统一调用入口；
- Schema：定义和校验工具输入输出；
- Policy：身份、权限、风险等级与调用策略；
- Execution：路由、执行、超时、取消和有限重试；
- Observability：日志、Trace、指标和执行历史；
- Audit：记录谁在何时以什么参数调用了什么工具；
- Console：可视化管理工具、执行记录和策略；
- Adapter：支持 HTTP/OpenAPI，并为 MCP 等协议提供适配层。

## 4.2 数据中台

数据中台将以用户可见的 Data Agent 作为第一个主要 Consumer，负责让用户安全地理解、发现和查询数据。

计划功能：

- 数据源连接和元数据发现；
- Catalog、表结构、字段语义和样例数据；
- 自然语言转 SQL；
- 只读查询与结果解释；
- 数据质量规则和异常检测；
- 数据血缘与指标口径；
- 查询权限、字段脱敏和敏感数据识别；
- 可构造的 synthetic data、标准问题集和 Ground Truth；
- 面向量化场景的行情、订单、成交、持仓、策略和风控数据模型。

它将优先复用工具中台中的：

```text
sql.list_tables
sql.describe_table
sql.sample_rows
sql.query_readonly
```

## 4.3 研发中台

研发中台将以 Developer Agent 面向用户，负责辅助量化策略、服务和内部工具的研发过程。

计划功能：

- 代码库检索与文件读取；
- Issue、需求与代码上下文关联；
- 代码生成、补丁生成和 Diff 审查；
- 单元测试、静态检查和构建执行；
- 依赖和变更影响分析；
- Git 分支、提交和 Pull Request 辅助；
- 研发规范、知识库和脚手架；
- 受控 Shell、沙箱和审批流程。

研发中台将大量使用工具中台提供的 Git、文件系统、搜索、构建和测试工具，因此在工具中台阶段应预留异步执行、长任务、流式日志和高风险审批的扩展点，但不需要立即实现完整能力。

## 4.4 运维中台

运维中台将以 Operations Agent 面向用户，负责系统运行状态的理解、诊断和受控操作。

计划功能：

- 日志、指标和 Trace 检索；
- 服务健康检查和依赖拓扑；
- 告警聚合、归因和处置建议；
- Runbook 检索与半自动执行；
- 发布状态、任务状态和容量分析；
- 故障时间线和复盘材料生成；
- 高风险变更审批与执行留痕。

## 4.5 安全中台

安全中台将以 Security Agent 面向用户，并负责跨所有中台的身份、策略、风险和合规治理。

计划功能：

- 身份、角色和服务账号；
- RBAC/ABAC 权限策略；
- Secret 生命周期和凭证引用；
- 工具风险分级；
- Prompt Injection 与恶意输入防护；
- 数据分类、脱敏和外发控制；
- 审批、审计和安全告警；
- 依赖漏洞、代码安全和策略检查。

首版工具中台会实现轻量权限与审计模型，但未来应允许安全中台成为统一策略来源，而不是让每个中台各自维护一套安全规则。

---

## 5. 已确认的关键技术决策

| 领域 | 决策 | 原因 |
|---|---|---|
| Control Plane 前端 | Next.js + TypeScript | 适合管理后台、类型安全、生态成熟 |
| 后端 | FastAPI + Python | 与数据、量化、Agent 和自动化生态衔接自然 |
| 数据库 | 云端托管 PostgreSQL | 应用不部署也能持久保存数据，保持标准 SQL 和可迁移性 |
| ORM 与迁移 | SQLAlchemy 2.x + Alembic | 模型清晰、迁移路径成熟、避免绑定具体云厂商 |
| 前后端协议 | REST + OpenAPI | 简单、可调试、FastAPI 可自动生成规范 |
| Agent 工具协议 | 核心使用平台内部契约，外层提供 MCP Adapter | 内核不绑定单一协议，同时便于 Agent 接入 |
| Tool Registry | 所有可被 Agent 调用的 Tool 都登记在数据库；实现来源分为平台原生与外部 MCP | 让目录、权限、版本、复用关系和执行历史拥有统一事实来源 |
| Agent—Tool 关系 | 数据库维护多对多绑定，Agent 运行时只获得已绑定且获授权的 Tool | 明确复用边界，避免把全量工具暴露给每个 Agent |
| 本地开发 | 前后端默认直接在宿主机运行 | 日志直观、断点方便、减少 Docker 引起的路径与网络问题 |
| 可复现演示 | 提供 Docker Compose 作为可选启动方式 | 便于展示和后续团队复现，但不作为首版日常调试硬依赖 |
| 执行模式 | 首版同步调用，模型预留异步任务状态 | 控制复杂度，同时不给长任务演进制造结构性障碍 |
| 用户模型 | 首版单用户可用，数据结构预留 workspace、principal 和 RBAC | 既保持轻量，又能展示团队化演进路线 |
| 代码组织 | Monorepo | 当前团队和规模下便于统一修改、演示和版本管理 |

云 PostgreSQL 不在架构层绑定厂商。Neon、Supabase、AWS RDS 或其他兼容 PostgreSQL 的托管服务均可通过 `DATABASE_URL` 接入。早期可选择 Neon 或 Supabase 以降低创建和管理成本。

---

## 6. 本地运行策略

为了兼顾“方便快速、报错少、好调试”和“能够稳定演示”，采用两种运行模式。

### 6.1 默认开发模式

默认模式是：

```text
Next.js Web       → 本机进程
FastAPI API       → 本机进程
Native Executor   → FastAPI 进程内或独立本机进程
PostgreSQL        → 云端托管服务
```

仓库提供一个统一脚本，例如：

```powershell
.\scripts\dev.ps1
```

脚本只负责检查环境并启动前后端，不隐藏错误输出。开发者仍可以单独启动 Web 或 API，以便断点调试。

默认模式的优点：

- 不要求开发者先理解容器网络；
- 前后端日志直接可见；
- IDE 断点和热更新简单；
- 云数据库已经提供持久化，因此首版无需维护本地数据库容器；
- 出错时容易判断是前端、后端、数据库连接还是工具本身的问题。

### 6.2 可复现演示模式

在项目骨架稳定后，增加 `compose.yaml`：

```text
docker compose up
```

它用于统一启动 Web、API 和需要隔离的 Tool Worker，但仍连接云 PostgreSQL。Compose 不应把数据库密码写入镜像或仓库，而是通过本地环境变量注入。

### 6.3 Docker 的边界

首版不要求所有工具进入容器。以下工具可直接在 API 进程中执行：

- Echo、时间等纯函数示例工具；
- 工具元数据读取；
- 受限的只读数据库查询。

当进入研发中台或出现不可信代码执行后，再将相关 Tool Worker 放入独立容器。此时容器是安全边界的一部分，而不只是为了“看起来云原生”。

---

## 7. Agent 平台与工具中台总体架构

平台在用户侧同时呈现 Agent 与 Tool；在工程侧仍以工具中台的 Control Plane / Execution Plane 为本版详细设计核心。Agent Catalog 与绑定关系属于 Control Plane，具体 Agent 的规划、记忆和领域工作流留到对应中台阶段实现。

```text
┌───────────────────────────────────────────────────────────────┐
│                         Control Plane                         │
│                                                               │
│  Web Console ── Control API ── Agent Catalog / Tool Registry  │
│       │               │                     │                 │
│       └───────────────┴──── Binding / Policy / Audit ─────────│
│                                      │                        │
└──────────────────────────────────────┼────────────────────────┘
                                       │ invoke / inspect
┌──────────────────────────────────────┼────────────────────────┐
│                         Execution Plane                       │
│                                      ▼                        │
│  Agent Runtime → Bound Tools → Tool Gateway                    │
│                      → Auth → Validation → Policy → Router     │
│                                               │               │
│                         ┌─────────────────────┴───────────┐    │
│                         ▼                                 ▼    │
│                Native Executor                     MCP Adapter │
│                Git / SQL / ...                    External MCP │
│                         └─────────────────────┬───────────┘    │
│                                               ▼               │
│                              Result / Error / Execution Log    │
└───────────────────────────────────────────────────────────────┘
                                       │
                                       ▼
                              Cloud PostgreSQL
```

### 7.1 Control Plane 的职责

Control Plane 管理“有哪些 Agent、有哪些 Tool、它们如何绑定、谁能使用、现在是什么状态”，但不承载复杂工具业务逻辑。

它负责：

- 创建和维护 Agent Catalog 与 Tool Definition；
- 管理 Agent—Tool 多对多绑定；
- 管理工具版本和 Schema；
- 配置风险等级、超时和重试策略；
- 启用或停用工具；
- 管理角色和授权关系；
- 查看执行记录、错误、耗时和调用方；
- 查看工具健康状态；
- 在页面中测试调用工具；
- 为未来审批流提供入口。

### 7.2 Execution Plane 的职责

Execution Plane 管理“一次调用如何被安全、确定地完成”。

所有可被 Agent 调用的 Tool 都通过统一 Gateway，并进入发现、权限、版本、执行记录和审计范围。平台内部不需要被 Agent 发现或调用的普通辅助函数只是实现代码，不属于 Tool，也不建立第二套本地工具目录。

它负责：

- 接收统一的调用请求；
- 认证调用者并生成请求上下文；
- 校验输入参数；
- 执行权限与风险策略；
- 根据工具类型和版本选择执行器；
- 设置超时、取消和有限重试；
- 标准化返回结果和错误；
- 写入执行记录、审计事件和 Trace 信息。

### 7.3 分层原则

- Control Plane 不直接包含具体 SQL、Git 或 Shell 业务实现；
- Tool Worker 不自行决定用户是否有权限，最终授权由统一策略层完成；
- Tool 定义与 Tool 实现分离：定义和绑定在数据库，平台原生实现位于本仓库，外部实现位于 MCP Server；
- Agent 只能看到其绑定关系、启用状态与权限策略交集中的 Tool；
- 调用协议与执行位置分离；
- 用户看到的错误与内部诊断信息分离；
- 审计记录与普通调试日志分离；
- Secret 只保存引用，不把明文凭证写入工具定义和执行历史。

---

## 8. Control Plane 详细设计

## 8.1 Web Console

前端使用 Next.js、React 和 TypeScript。UI 重点是把架构能力展示清楚，而不是追求复杂视觉效果。

建议页面：

### Overview

展示：

- 已注册工具数量；
- 已启用和停用数量；
- 最近调用次数；
- 成功率和平均耗时；
- 最近失败；
- 按风险等级分布。

### Agents

展示数据、研发、运维、安全等 Agent 的名称、说明、状态和已绑定 Tool 数量。Agent 详情页展示其可用 Tool、绑定版本策略和最近调用；本阶段只实现目录与绑定管理，不实现四类领域 Agent 的完整运行逻辑。

### Tools

展示 Registry 数据库中的全部 Agent 可调用 Tool，并支持按 namespace、状态、风险等级和提供方类型筛选。提供方类型至少包含 `native` 与 `mcp`。

页面提供 Tool 注册入口和新版本发布入口；所有提交均经过后端校验后写入 Registry。平台原生 Tool 的执行路由指向受控 `handler_key`，外部 MCP Tool 的执行路由指向 MCP Server 和远端 Tool 名称。

工具详情页包含：

- 名称、说明、Owner 和标签；
- 当前版本与历史版本；
- 输入输出 JSON Schema；
- 所需权限；
- 风险等级；
- 超时和重试配置；
- Executor 类型及健康状态；
- 实现来源：平台原生或外部 MCP；
- 当前绑定并复用该 Tool 的 Agent；
- 最近执行记录；
- 内置 Playground。

### Executions

展示：

- execution_id；
- agent、tool、version；
- caller / principal；
- status；
- started_at、duration；
- error_code；
- trace_id。

详情页展示完整阶段时间线，但默认对敏感参数和结果脱敏。

### MCP Connections

展示已登记的外部 MCP Server、连接状态、最后发现时间和可导入 Tool。发现、导入与刷新都由用户显式触发，并展示 Schema 差异与版本处理结果。

### Policies

首版只需要展示简单 RBAC：

- Role；
- Permission；
- Role 与 Permission 的关系；
- 工具需要的 Permission；
- Allow / Deny 结果说明。

### Audit

展示关键不可抵赖事件：

- 工具创建或修改；
- 工具启停；
- 权限修改；
- 高风险工具调用；
- 策略拒绝；
- Secret 引用变更。

### Settings

首版只放展示性配置，例如默认超时、日志保留说明、数据库连接状态和运行环境，不在页面暴露 Secret 明文。

## 8.2 Control API

Control API 由 FastAPI 提供，主要端点建议如下：

```text
GET    /api/v1/tools
POST   /api/v1/tools
GET    /api/v1/tools/{tool_id}
PATCH  /api/v1/tools/{tool_id}
POST   /api/v1/tools/{tool_id}/versions
POST   /api/v1/tools/{tool_id}/enable
POST   /api/v1/tools/{tool_id}/disable

GET    /api/v1/agents
POST   /api/v1/agents
GET    /api/v1/agents/{agent_id}
PUT    /api/v1/agents/{agent_id}/tools/{tool_id}
DELETE /api/v1/agents/{agent_id}/tools/{tool_id}

GET    /api/v1/mcp-servers
POST   /api/v1/mcp-servers
POST   /api/v1/mcp-servers/{server_id}/discover
POST   /api/v1/mcp-servers/{server_id}/import

GET    /api/v1/executions
GET    /api/v1/executions/{execution_id}

GET    /api/v1/roles
GET    /api/v1/permissions
PUT    /api/v1/roles/{role_id}/permissions

GET    /api/v1/audit-events
GET    /api/v1/health
```

即使首版是单用户，也不应把身份硬编码在所有业务逻辑中。开发环境可以由一个 `LocalIdentityProvider` 注入固定开发者身份；未来可替换为真正的 OIDC Provider。

## 8.3 Tool Registry

Registry 是工具中台的核心元数据层。工具应使用稳定标识：

```text
namespace.name@version
```

示例：

```text
system.echo@1.0.0
sql.list_tables@1.0.0
sql.query_readonly@1.1.0
```

Registry 至少保存：

- 唯一工具名称；
- 展示名称与描述；
- Owner；
- 标签；
- 语义化版本；
- 输入和输出 JSON Schema；
- 执行器类型和路由配置；
- 风险等级；
- 所需权限；
- 默认超时；
- 重试策略；
- 启用状态；
- 创建和修改时间。

Registry 管理全部可被 Agent 调用的 Tool。数据库是工具定义、版本、Schema、实现路由、运行状态和 Agent 绑定关系的运行时权威来源。平台不从本地 Manifest 隐式同步定义。

平台原生 Tool 通过 Control Plane、Registration API 或受控 seed 显式登记，执行实现保存在本仓库；外部 MCP Tool 则通过一次显式的发现和导入操作登记为数据库快照，执行实现仍在外部 MCP Server。两类 Tool 在目录、绑定、权限、调用和审计层使用同一套模型。

---

## 9. Execution Plane 详细设计

## 9.1 Tool Gateway

所有调用通过统一入口：

```text
POST /api/v1/tools/{namespace}/{name}:invoke
```

建议请求结构：

```json
{
  "version": "1.0.0",
  "arguments": {
    "message": "hello"
  },
  "context": {
    "agent_id": "agent_data",
    "request_source": "console-playground",
    "idempotency_key": "optional-client-key"
  }
}
```

`agent_id` 不是由任意调用者自报后直接信任。真实 Agent Runtime 使用与 Agent 绑定的服务身份，Gateway 校验二者关系；Control Plane Playground 由获授权的开发者显式选择“以哪个 Agent 测试”，并记录审计事件。

建议响应结构：

```json
{
  "execution_id": "exec_01...",
  "trace_id": "trace_01...",
  "status": "succeeded",
  "data": {
    "message": "hello"
  },
  "error": null,
  "meta": {
    "tool": "system.echo",
    "version": "1.0.0",
    "duration_ms": 12
  }
}
```

标准状态：

```text
accepted
running
succeeded
failed
timed_out
cancelled
denied
```

首版的 HTTP 请求可以同步等待最终结果，但数据库状态仍使用上述状态机，方便未来扩展为异步任务。

## 9.2 一次执行的标准流程

```text
1. Receive Request
2. Resolve Identity
3. Resolve Agent + Tool Binding
4. Resolve Tool + Version
5. Validate Input Schema
6. Evaluate Policy
7. Create Execution Record
8. Resolve Executor
9. Execute with Timeout
10. Validate / Normalize Output
11. Persist Result Metadata
12. Append Audit Event
13. Return Standard Response
```

重要原则：即使参数校验或权限校验失败，也应生成轻量审计记录；但不得在审计记录中泄露不应保存的完整 Secret 或敏感字段。

## 9.3 Executor 抽象

平台定义统一接口，例如：

```python
class ToolExecutor(Protocol):
    async def execute(
        self,
        definition: ToolDefinition,
        arguments: dict,
        context: ExecutionContext,
    ) -> ToolResult:
        ...
```

规划中的执行器类型：

| 类型 | 首版 | 用途 |
|---|---:|---|
| NativeExecutor | 是 | 通过受控 `handler_key` 运行本仓库中的平台原生 Tool |
| HttpExecutor | 是或第二阶段 | 调用独立 HTTP Tool Server |
| ContainerExecutor | 预留 | 隔离不可信或依赖复杂的执行任务 |
| AsyncJobExecutor | 预留 | 构建、测试、批处理等长任务 |
| MCPExecutor / Adapter | 适配 | 将 MCP 工具映射到平台契约，或向 MCP Client 暴露平台工具 |

业务层只依赖 `ToolExecutor` 接口，不依赖工具实际位于同一进程、另一进程还是容器中。

## 9.4 超时、重试和幂等

- 每个工具必须配置最大超时；
- Gateway 还有一个平台级超时上限；
- 只有明确标记为 `retry_safe` 的工具才能自动重试；
- 首版最多重试一次，避免掩盖真实故障；
- 写操作默认不重试；
- 支持可选 `idempotency_key`，为未来写操作防重提供基础；
- 超时后记录 `timed_out`，不能简单记录为普通失败；
- 未来异步 Worker 需要支持协作式取消。

## 9.5 错误模型

统一错误码，避免前端和 Agent 解析任意异常文本：

```text
TOOL_NOT_FOUND
TOOL_VERSION_NOT_FOUND
TOOL_DISABLED
INPUT_VALIDATION_FAILED
PERMISSION_DENIED
APPROVAL_REQUIRED
EXECUTION_TIMEOUT
EXECUTOR_UNAVAILABLE
TOOL_EXECUTION_FAILED
OUTPUT_VALIDATION_FAILED
RATE_LIMITED
INTERNAL_ERROR
```

响应中可以包含面向用户的安全错误信息；详细堆栈仅写入本地开发日志，不写入公开 API 响应。

---

## 10. 统一 Tool Registry 与实现来源

平台只有一个面向 Agent 的 Tool Catalog。任何希望被一个或多个 Agent 发现和调用的能力，都必须先在中央 Tool Registry 中拥有定义和已发布版本。平台不再建立“数据库工具”和“本地工具”两套目录。

### 10.1 平台原生 Tool

平台原生 Tool 占本项目绝大多数，例如 Git、数据库、日志和系统工具。它们采用“数据库定义 + 本仓库实现”的方式：

- Registry 保存名称、描述、版本、输入输出 JSON Schema、风险、权限、状态和 `handler_key`；
- 本仓库保存经过审核的执行代码，`NativeExecutor` 只允许调用白名单中的 `handler_key`；
- 注册是显式发布操作，可以通过 Control Plane、Registration API 或受控 seed 完成；
- 修改代码不会自动改写 Registry，修改 Registry 也不会生成代码；
- 发布前必须校验 `handler_key` 存在，并验证实现与输入输出 Schema 一致；
- 已发布版本不可原地修改，代码或契约变更应发布新版本；
- 数据库不保存 Python/JavaScript 源代码，只保存调用契约与稳定路由。

平台内部的格式化、Repository、校验器等普通函数如果不需要被 Agent 发现和调用，就只是应用实现，不应伪装成 Tool，也不进入 Registry。

原生 Tool 注册示例：

```json
{
  "namespace": "sql",
  "name": "query_readonly",
  "display_name": "Read-only SQL Query",
  "version": "1.0.0",
  "provider_type": "native",
  "description": "Execute a read-only PostgreSQL query.",
  "risk_level": "medium",
  "required_permissions": ["database.read"],
  "timeout_seconds": 10,
  "executor": {
    "type": "native",
    "handler_key": "sql.query_readonly"
  },
  "input_schema": {
    "type": "object",
    "additionalProperties": false,
    "required": ["connection_ref", "query"],
    "properties": {
      "connection_ref": {"type": "string"},
      "query": {"type": "string"},
      "max_rows": {"type": "integer", "minimum": 1, "maximum": 1000}
    }
  },
  "output_schema": {
    "type": "object",
    "required": ["columns", "rows", "row_count"]
  }
}
```

### 10.2 外部 MCP Tool

外部 MCP Tool 的实现和生命周期由外部 MCP Server 负责，本平台只负责接入、治理与调用：

```text
管理员登记 MCP Server
→ 平台调用 tools/list 进行发现
→ 管理员选择要导入的 Tool
→ Tool Definition / Schema 作为版本快照写入 Registry
→ Agent 通过统一 Gateway 调用
→ MCP Adapter 转发到外部 Server
```

这类 Tool 遵循以下规则：

- Registry 记录 `provider_type=mcp`、`mcp_server_id`、远端 Tool 名称和已导入 Schema；
- 外部团队不需要本项目 Git 权限，只需要提供可访问的 MCP Server 和授权信息；
- Secret 只保存引用，不把 Token 明文写入 Registry；
- 发现、首次导入和刷新都是显式操作，不进行不可见的后台双向同步；
- 外部 Tool 的 Schema 发生变化时，刷新操作创建新版本或给出破坏性变更提示，不原地篡改已发布版本；
- MCP 不绕过 Gateway；身份、绑定、权限、超时、执行记录和审计规则与原生 Tool 一致。

### 10.3 Agent—Tool 多对多复用

Agent Catalog 与 Tool Registry 通过 `agent_tool_bindings` 建立多对多关系：

```text
Data Agent      ─┬─ sql.query_readonly
Developer Agent ─┼─ git.read_file
Security Agent  ─┘─ git.read_file
```

- 一个 Agent 可以绑定多个 Tool；
- 一个 Tool 可以被多个 Agent 复用；
- 绑定只表达“该 Agent 被配置为可使用”，最终调用仍需通过身份和 Policy；
- Agent Runtime 只向模型暴露“已绑定、已启用、版本可用、权限允许”的 Tool；
- Tool 详情页反向显示 Consumer Agents，Agent 详情页显示 Bound Tools；
- 绑定可以固定版本、指定兼容版本范围，或跟随 Registry 默认稳定版本；
- 删除绑定不会删除 Tool，也不会影响其他 Agent 的绑定。

### 10.4 Tool 版本规则

- 文档或非破坏性元数据修改：PATCH；
- 增加可选参数或兼容字段：MINOR；
- 删除字段、改变语义或不兼容修改：MAJOR；
- 已发布版本不可原地改变输入输出契约；
- 调用方未指定版本时，使用 Registry 配置的默认稳定版本；
- 执行记录必须保存实际解析后的精确版本；
- 新版本注册后先处于草稿或测试状态，验证后再设置为默认版本。

---

## 11. 权限、风险与安全边界

## 11.1 首版权限模型

采用简化 RBAC：

```text
Principal → Role → Permission → Tool
```

示例角色：

```text
platform_admin
tool_developer
tool_viewer
agent_runtime
```

示例权限：

```text
tool.read
tool.manage
tool.invoke
execution.read
audit.read
database.read
```

本地开发身份可以默认获得管理员角色，但所有调用仍经过 Policy Service，以证明权限链路是真实存在的，而不是只在 UI 上展示。

## 11.2 风险等级

建议四级：

| 等级 | 示例 | 默认控制 |
|---|---|---|
| Low | echo、读取公开元数据 | 允许有权限的身份直接调用 |
| Medium | 只读 SQL、读取代码文件 | 权限校验、限流、审计、超时 |
| High | 写数据库、创建分支、运行构建 | 明确授权，未来接审批 |
| Critical | 删除资源、生产变更、任意 Shell | 首版禁用，未来强审批与隔离 |

## 11.3 Secret 管理

首版遵循以下规则：

- `.env` 只存在本地，不提交；
- 提交 `.env.example`，只写变量名和说明；
- 数据库强制 SSL；
- Registry 保存 `connection_ref`，不保存连接密码；
- 执行参数、日志和审计输出支持字段级脱敏；
- API 响应永远不返回服务端 Secret；
- 未来可将本地环境变量替换为 Vault 或云 Secret Manager，工具契约无需变化。

## 11.4 SQL 工具安全

只读 SQL 工具应采取多层限制：

- 使用数据库只读账号；
- 只允许单条查询；
- 拒绝 INSERT、UPDATE、DELETE、DDL 和危险函数；
- 设置 statement timeout；
- 设置最大返回行数；
- 限制允许访问的 schema；
- 对敏感列提供脱敏或拒绝策略；
- 记录查询摘要，敏感参数按策略脱敏。

仅靠字符串正则判断 SQL 是否只读是不够的。首版可以使用 SQL Parser 做基础检查，但数据库只读账号才是最终安全边界。

---

## 12. 数据模型

建议首版包含以下核心表。

### workspaces

为未来多团队隔离预留。首版只有一个默认 workspace。

```text
id, name, slug, created_at
```

### principals

```text
id, workspace_id, type, display_name, external_id, status, created_at
```

`type` 可以是 `user`、`service_account` 或 `agent`。

### agents

保存用户可见的 Agent Catalog 条目。本版只管理目录和 Tool 绑定，不在此表展开各领域 Agent 的 Prompt、Memory 或工作流内部设计。

```text
id, workspace_id, namespace, name, display_name, description,
agent_type, status, owner, created_at, updated_at
```

### roles / permissions / role_permissions / principal_roles

表达基础 RBAC 关系。

### tools

```text
id, workspace_id, namespace, name, display_name, description,
owner, provider_type, risk_level, status, default_version,
created_at, updated_at
```

`provider_type` 首版为 `native` 或 `mcp`。

### tool_versions

```text
id, tool_id, version, input_schema, output_schema,
executor_type, executor_config, timeout_seconds,
retry_policy, required_permissions, definition_hash,
registration_channel, created_by_principal_id,
created_at, deprecated_at
```

`registration_channel` 记录 Tool 通过 `console`、`api`、`mcp_import` 或 `seed` 中的哪一种方式进入 Registry。`executor_config` 对原生 Tool 保存 `handler_key`，对 MCP Tool 保存 `mcp_server_id` 与远端 Tool 名称。无论入口是什么，注册完成后的数据库记录都是可审计版本快照，不与来源持续隐式同步。

### agent_tool_bindings

```text
id, agent_id, tool_id, version_policy, enabled, configuration,
created_by_principal_id, created_at, updated_at
```

`agent_id + tool_id` 唯一。`version_policy` 可以跟随默认稳定版本、固定精确版本或声明兼容范围。

### mcp_servers

```text
id, workspace_id, name, transport, endpoint, auth_secret_ref,
status, last_discovered_at, created_at, updated_at
```

这里只保存连接配置与 Secret 引用，不复制外部实现，也不保存认证明文。

### executions

```text
id, workspace_id, agent_id, agent_tool_binding_id, tool_id,
tool_version_id, principal_id,
status, request_source, arguments_redacted, result_redacted,
error_code, error_message_safe, trace_id, idempotency_key,
started_at, finished_at, duration_ms
```

### audit_events

```text
id, workspace_id, actor_principal_id, action, resource_type,
resource_id, decision, metadata_redacted, trace_id, created_at
```

### tool_health_checks

可在第二阶段加入：

```text
id, tool_version_id, status, latency_ms, message, checked_at
```

所有业务表使用 UTC 时间存储。前端根据用户时区展示。

---

## 13. 可观察性与审计

首版目标不是搭建完整监控集群，而是把正确的观察字段贯穿起来。

每次请求生成：

```text
request_id
execution_id
trace_id
```

结构化日志至少包含：

```text
timestamp
level
service
environment
trace_id
execution_id
tool_name
tool_version
principal_id
event
duration_ms
error_code
```

建议阶段划分：

```text
gateway.receive
identity.resolve
tool.resolve
schema.validate
policy.evaluate
executor.start
executor.finish
result.persist
gateway.respond
```

首版可以使用标准结构化日志和数据库执行记录，不必立即部署 Prometheus、Grafana 和 OpenTelemetry Collector。但代码应使用 OpenTelemetry 兼容的 Trace 抽象，后续接入时无需重写业务流程。

审计与日志区别：

- 日志用于排错，可以按保留周期清理；
- 审计用于回答谁做了什么，字段更加稳定；
- 审计记录不保存 Secret；
- 高风险操作即使失败也应有审计事件。

---

## 14. 首版示例工具

首版建议只实现少量工具，用来证明不同能力，不追求数量。

| 工具 | 用途 | 证明的能力 |
|---|---|---|
| `system.echo` | 原样返回输入 | 注册、Schema、执行、日志全链路 |
| `system.current_time` | 返回服务端 UTC 时间 | 无副作用平台原生 Tool |
| `sql.list_tables` | 列出允许的表 | 云数据库连接与权限 |
| `sql.describe_table` | 返回表结构 | 参数校验、结构化结果 |
| `sql.query_readonly` | 受控只读查询 | 风险策略、超时、行数限制、审计 |
| `http.health_check` | 检查允许列表中的 HTTP 服务 | HttpExecutor 与网络错误标准化 |

如果时间有限，前三个即可形成第一条端到端链路；其余工具依次增加不同架构证明点。

不建议首版提供任意 Shell 工具。它会引入进程隔离、文件系统边界、网络访问、命令白名单和资源限制等问题，更适合研发中台阶段单独实现。

---

## 15. MCP 与外部接入

平台内部的事实来源是 Tool Definition、Agent—Tool Binding 和统一执行接口，不把 MCP 协议本身当成领域数据模型。MCP Adapter 包含两个方向：向外部 MCP Server 发起调用，以及未来把本平台获授权的 Tool 以 MCP Server 形式提供给外部 Client。

外部 MCP Tool 的接入路径：

```text
External MCP Server
    │ tools/list / tools/call
    ▼
MCP Client Adapter
    │ import snapshot / invoke
    ▼
Tool Registry / Tool Gateway
```

本平台 Tool 对外暴露路径：

```text
MCP Client
    │ tools/list
    │ tools/call
    ▼
MCP Adapter
    │
    ▼
Tool Gateway
```

映射原则：

- `tools/list` 只返回调用者有权看到且已启用的工具；
- MCP input schema 来自 Registry；
- `tools/call` 仍必须经过身份、策略、超时和审计；
- MCP 返回错误映射自平台标准错误码；
- MCP Adapter 不是绕过 Gateway 的旁路。

首版先稳定 HTTP/OpenAPI 调用链路和原生 Tool，再增加外部 MCP 导入/调用 Adapter，最后按需要增加对外 MCP Server Adapter。这样 Web Playground、Agent Runtime、自动化测试和 MCP Client 都复用同一个执行核心。

---

## 16. 推荐仓库结构

```text
agent-platform/
├─ apps/
│  ├─ web/                    # Next.js Control Plane
│  └─ api/                    # FastAPI Control API + Gateway
├─ packages/
│  ├─ ui/                     # 可复用前端组件
│  ├─ contracts/              # OpenAPI 生成类型或共享契约
│  └─ sdk-typescript/         # 未来供 TS Consumer 使用
├─ services/
│  ├─ tool-runtime/           # 执行器、工具上下文与结果模型
│  └─ mcp-adapter/            # 外部 MCP 发现、导入与调用适配
├─ tools/
│  └─ native/                 # 平台原生 Tool 的受控实现
│     ├─ system/
│     ├─ sql/
│     └─ git/
├─ executors/
│  ├─ native/                 # 根据 handler_key 调用原生 Tool
│  ├─ http/                   # 外部 HTTP Tool Service 调用适配
│  └─ mcp/                    # 外部 MCP Server 调用适配
├─ migrations/                # Alembic migrations
├─ tests/
│  ├─ unit/
│  ├─ integration/
│  └─ e2e/
├─ scripts/
│  ├─ dev.ps1
│  ├─ check.ps1
│  └─ seed_demo.ps1
├─ docs/
│  ├─ architecture/
│  ├─ adr/
│  └─ api/
├─ compose.yaml               # 可选可复现运行方式
├─ .env.example
├─ README.md
└─ plan.md
```

实际开发时可以先把 `services/tool-runtime` 放在 API 项目内部，待出现第二个调用者或独立 Worker 时再抽成包。目录表达的是清晰边界，不要求第一天就拆成多个可发布组件。

---

## 17. 前后端开发约定

## 17.1 前端

- TypeScript 开启严格模式；
- API 类型从 OpenAPI 生成，避免重复手写；
- 使用成熟的组件库完成管理后台，不自研基础 UI；
- 页面区分 Loading、Empty、Error 和 Permission Denied 状态；
- 执行详情使用阶段时间线展示；
- JSON Schema 和参数使用专门的 JSON/Schema Viewer；
- 前端不能自行判断最终权限，只负责展示后端决策。

## 17.2 后端

- FastAPI 路由层只负责协议转换；
- Application Service 编排 Registry、Policy 和 Executor；
- Domain Model 不依赖 FastAPI；
- Repository 层隔离 SQLAlchemy；
- Pydantic 模型区分 API DTO 与数据库模型；
- 所有外部调用必须配置超时；
- 使用依赖注入切换 LocalIdentityProvider、Executor 和 SecretProvider；
- 错误统一映射为平台错误码。

## 17.3 契约同步

FastAPI 生成 OpenAPI；前端在开发或 CI 中生成 TypeScript Client。JSON Schema 是工具参数的事实来源，Pydantic 用于平台 API 的服务端校验。

---

## 18. 测试与评估策略

测试分为四层。

### 单元测试

覆盖：

- Registration API 输入校验；
- Tool 版本不可变规则；
- 原生 `handler_key` 白名单解析；
- Agent—Tool 绑定与版本策略；
- MCP 发现结果导入与破坏性变更判断；
- Schema 校验；
- Policy 决策；
- 版本解析；
- 超时和错误映射；
- 敏感字段脱敏。

### 集成测试

覆盖：

- API 与云测试数据库；
- Alembic Migration；
- Registry 创建、更新、启停与版本发布；
- NativeExecutor；
- MCP Adapter；
- 只读 SQL 限制；
- 执行记录和审计的一致性。

### 端到端测试

覆盖核心演示路径：

```text
登录为本地开发身份
→ 查看 Agent 列表
→ 打开 Agent 并查看已绑定 Tool
→ 查看工具列表
→ 打开工具详情
→ 在 Playground 输入参数
→ 调用工具
→ 查看结果
→ 在 Executions 找到此次调用
→ 在 Audit 中确认记录
```

### 架构场景测试

这些测试用于证明设计，而不是只证明函数能运行：

- 停用工具后调用被拒绝；
- 输入不符合 Schema 时执行器不会启动；
- 无权限调用产生 `PERMISSION_DENIED`；
- 超时被标记为 `timed_out`；
- 敏感参数不会原样进入执行历史；
- 旧工具版本仍可被明确调用；
- 未绑定的 Agent 无法获得该 Tool；
- 同一个 Tool 绑定给多个 Agent 时只维护一份定义和实现；
- 同一 Tool Definition 可以从 NativeExecutor 迁移到远程 Executor，而调用端不变。

未来数据中台的 Eval 会在此基础上增加“问题—SQL—执行结果—Ground Truth”的自动评估，但不属于本阶段。

---

## 19. 开发阶段与里程碑

## Phase 0：项目骨架与决策固化（已完成）

目标：所有人能理解并启动项目基础结构。

交付：

- Monorepo 骨架；
- Next.js 和 FastAPI 空应用；
- 云 PostgreSQL 连接；
- 配置加载和 `.env.example`；
- Alembic 初始迁移；
- 健康检查；
- 本地启动脚本；
- 基础 ADR。

验收：

- 一条命令可启动前后端；
- Web 能展示 API 和数据库连接状态；
- 新开发者无需阅读大量代码即可找到入口。

## Phase 1：端到端最小闭环（已完成）

目标：证明 Agent Catalog、统一 Tool Registry、Agent—Tool 复用关系和原生 Tool 执行的完整链路。

交付：

- Agent Catalog、Tool Registry 和 `agent_tool_bindings` 数据模型；
- Tool Registration API；
- Tool 的不可变版本模型；
- Data Agent、Developer Agent 两个目录占位条目；
- 数据库中注册、代码中实现的原生示例 Tool `system.echo`；
- Agent—Tool 绑定 API；
- Tool Gateway；
- 输入输出 Schema 校验；
- Execution Record；
- 标准错误模型；
- Agent 列表与详情、Tool 列表与详情、绑定管理和 Playground 页面。

验收：

- 页面可以注册、发现和调用数据库中的 `system.echo`；
- `system.echo` 只实现和注册一次，但可以同时绑定给 Data Agent 与 Developer Agent；
- Agent 详情可看到 Bound Tools，Tool 详情可看到 Consumer Agents；
- 未绑定该 Tool 的 Agent 不会在运行时获得它；
- 重复注册同名同版本时遵守幂等或冲突规则；
- 每次调用都有 execution_id 和 trace_id；
- 错误输入有清晰、结构化的错误反馈。

## Phase 2：权限、审计与代表性工具（已完成）

目标：证明平台治理能力，而不是只有工具目录。

交付：

- LocalIdentityProvider；
- 简化 RBAC；
- 风险等级；
- Audit Event；
- `sql.list_tables`、`sql.describe_table`、`sql.query_readonly`；
- 将 SQL Tool 绑定给 Data Agent，并用权限策略控制其他 Agent 的使用；
- 超时、有限重试和脱敏；
- Executions、Policies、Audit 页面。

验收：

- 无权限身份无法调用受限工具；
- SQL 使用只读连接并受行数、超时和 schema 限制；
- 管理页面可以解释一次调用为什么成功或被拒绝。

## Phase 3：扩展性展示与演示打磨（已完成）

目标：让项目能够清楚说明未来演进方式。

交付：

- HttpExecutor；
- MCP Server 管理、显式发现/导入和 MCP Client Adapter；
- 工具版本与废弃状态；
- Docker Compose 演示模式；
- 架构图、演示数据和 Demo Script；
- 关键指标卡片；
- 完整的 README 和故障排查说明。

实现说明：统一 Gateway 依据不可变 `ToolVersion.executor_type` 分派到 Native、HTTP 或
MCP Executor；外部 MCP Server 必须先登记、显式发现，再由管理员选择 Tool 导入，平台
不会做隐式同步。平台同时提供独立 MCP facade，让标准 MCP Client 只能看到指定 Agent、
指定 Principal 在当下策略下获授权的 Tool。

验收：

- 同一入口可调用原生、HTTP 和外部 MCP Tool；
- 外部 MCP Tool 可以显式导入 Registry、绑定给 Agent 并留下统一执行记录；
- MCP Client 能发现并调用本平台获授权工具；
- 在另一台开发机上可按文档完成演示；
- 演示能够直观说明 Control Plane 与 Execution Plane 的差异。

## Phase 4：为数据中台准备接口（已完成）

此阶段仍不展开数据中台内部架构，只完成工具中台的交接准备：

- 稳定 SQL 工具契约；
- 为 Agent 身份建立 service account；
- 提供 TypeScript 或 Python SDK；
- 建立数据中台调用示例；
- 明确工具发现、执行和审计接口的兼容性承诺。

实现说明：SQL Tool `1.0.0` 契约进入 stable 状态；新增只能代表 Data Agent 的
`data-agent-runtime` service account；交付独立 Python SDK、机器可读 compatibility
endpoint 和端到端消费示例。此阶段只固定工具中台与未来数据中台的边界，不预设数据
中台内部的编排、记忆、语义层或评测架构。

验收：

- service account 可以发现并调用 Data Agent 获授权的 SQL Tool；
- service account 代表其他 Agent 时被 `AGENT_SCOPE_DENIED` 拒绝并留下审计；
- Python SDK 保留结构化错误、execution_id 与 trace_id；
- 示例可以查询 `tool_data.market_prices`，Agent runtime 不接触数据库凭据；
- API v1 与 SQL Tool v1 的兼容性规则同时提供文档和机器可读接口。

---

## 20. Demo 场景

建议最终演示控制在 8 至 12 分钟，依次展示：

1. 打开 Overview，说明平台同时管理 Agent 与可复用 Tool；
2. 打开 Data Agent，查看它绑定的 SQL Tool；
3. 打开 `sql.query_readonly`，查看版本、Schema、权限、实现来源和 Consumer Agents；
4. 在 Playground 以 Data Agent 身份输入一个合法查询并执行；
5. 展示标准化结果、耗时、execution_id 和 trace_id；
6. 打开 Execution Detail，查看调用阶段；
7. 切换到未绑定或无数据库权限的 Agent 并再次调用；
8. 展示拒绝结果和对应审计记录；
9. 展示同一个 Git Tool 同时被研发 Agent 与安全 Agent 复用；
10. 展示一个外部 MCP Tool 与原生 Tool 通过同一 Gateway 调用。

这个 Demo 同时证明功能、治理能力和架构扩展性，比展示大量相似工具更有说服力。

---

## 21. 建议记录的架构决策 ADR

当前已接受和后续建议补充的 ADR：

```text
ADR-001 采用 Control Plane / Execution Plane 分层
ADR-002 Control Plane 使用 Next.js + TypeScript
ADR-003 使用云端托管 PostgreSQL，但保持厂商中立
ADR-004 默认宿主机开发，Docker Compose 作为可选演示模式
ADR-005 平台内部契约与 MCP Adapter 分离
ADR-006 已废弃：数据库通用工具与代码内本地工具分离
ADR-007 Agent Catalog、统一 Tool Registry 与多对多复用
ADR-008 首版同步执行，数据模型预留异步状态
ADR-009 首版简化 RBAC，预留外部 Policy Provider
ADR-010 不在首版提供任意 Shell 执行
```

每份 ADR 只需包含背景、决策、备选方案、结果和未来复审条件。这样可以展示设计是有取舍的，而不是偶然堆叠技术。

---

## 22. 主要风险与应对

| 风险 | 表现 | 应对 |
|---|---|---|
| 过度设计 | 为未来功能提前建设大量服务 | 以当前闭环为准，只保留接口和数据字段扩展点 |
| 工具数量驱动 | 花大量时间写相似工具 | 每个示例工具必须证明一种新架构能力 |
| 本地环境复杂 | Docker、Node、Python、数据库同时报错 | 默认宿主机运行，统一脚本做环境检查，错误分层展示 |
| 云数据库泄密 | 连接串进入仓库或日志 | `.env`、Secret 引用、日志脱敏、只读账号和 SSL |
| 动态执行风险 | Shell 或 SQL 能力过强 | 首版不做任意 Shell，SQL 多层只读控制 |
| 协议锁定 | 核心模型绑定 MCP 或某一 SDK | 内部统一 Tool Contract，协议放在 Adapter 层 |
| 前后端模型漂移 | TS 和 Python 各自定义结构 | OpenAPI 生成 Client，JSON Schema 作为工具契约来源 |
| 审计不可用 | 日志很多但无法回答谁做了什么 | 单独 Audit Event 模型，身份和 trace_id 全链路传递 |
| 版本破坏调用方 | 工具 Schema 被原地修改 | 不可变版本、语义化版本、默认稳定版本和废弃期 |
| Registry 数据误改或丢失 | Tool 定义和 Agent 绑定只在数据库中维护 | 数据库备份、不可变版本、审计事件、导出能力和受控管理 API |
| Agent 获得过多 Tool | 模型误调用与攻击面扩大 | 显式绑定、最小权限、运行时按绑定与 Policy 交集过滤 |
| 原生实现与定义漂移 | handler 或 Schema 不匹配 | 发布前解析 handler、契约测试、definition hash 和版本化发布 |
| 外部 MCP 变更 | 远端 Schema 或可用性变化 | 显式刷新、版本差异检查、健康状态和已发布快照不可变 |

---

## 23. 首版完成定义

当以下条件全部满足时，可以认为工具中台首版完成：

- 本地可稳定启动 Web 和 API；
- 云 PostgreSQL 可正常迁移和持久化；
- 页面可查看、筛选和打开工具；
- 至少一个系统工具和一个数据库工具完成端到端执行；
- 调用会经过身份、Schema、Policy、Executor 和审计链路；
- 失败、拒绝和超时具有统一状态及错误码；
- 执行历史可根据 execution_id 或 trace_id 排查；
- 敏感字段不会直接出现在日志或页面；
- Agent Catalog、统一 Tool Registry、多对多绑定和版本规则边界清晰；
- 原生 Tool 与外部 MCP Tool 的实现来源、注册和调用路径清晰；
- HTTP/OpenAPI 接口稳定，MCP 导入与调用路径明确；
- 文档能够解释未来四个中台如何使用和扩展工具中台；
- 项目 Demo 能在十分钟左右完整展示设计价值。

---

## 24. 推荐的第一批开发任务

按依赖顺序建议先建立以下任务：

1. 初始化 Monorepo、Next.js 和 FastAPI；
2. 选择一个托管 PostgreSQL 实例并创建只用于平台元数据的数据库账号；
3. 建立配置加载、健康检查和 Alembic；
4. 创建 `agents`、`tools`、`tool_versions`、`agent_tool_bindings`、`executions` 和 `audit_events`；
5. 实现 Agent Catalog、Tool Registration API 和数据库版本发布规则；
6. 通过 Registration API 注册 `system.echo` 并实现 NativeExecutor；
7. 建立 Data Agent、Developer Agent 与 `system.echo` 的复用绑定；
8. 实现统一 Invoke API 和错误模型；
9. 实现 Agent/Tool 列表、双向关系详情、绑定管理与 Playground；
10. 增加 LocalIdentityProvider 和最小 RBAC；
11. 增加 SQL 只读工具和数据库安全限制；
12. 增加 Execution/Audit 页面；
13. 增加 MCP Server 发现、显式导入和调用适配；
14. 补充架构场景测试、Demo 数据和演示脚本。

前九项完成后就已经有一个 Agent 可见、Tool 可注册、关系可复用、调用可追踪的最小闭环；后续任务用于把它从“执行 Demo”提升为“Agent + Tool 平台 Demo”。

---

## 25. 结论

本项目的第一阶段应专注于建立一个边界清晰的 Agent + Tool 平台：Control Plane 负责展示 Agent Catalog、Tool Registry、复用绑定和治理，Execution Plane 负责可靠、安全、可观察的执行。Next.js/TypeScript 提供可视化控制面，FastAPI/Python 提供统一 API 与执行核心，云 PostgreSQL 提供持久化。

首版默认直接在本机运行前后端，以获得最简单的调试体验；Docker Compose 作为可复现演示和未来执行隔离的补充方案。平台只实现少量代表性工具，但完整呈现注册、发现、权限、执行、错误、审计和版本链路。

所有可被 Agent 调用的 Tool 都进入统一 Registry。绝大多数平台原生 Tool 的实现保存在本仓库，外部 MCP Tool 的实现保留在远端；二者共享发现、Agent 绑定、权限、调用和审计模型。普通内部辅助函数不是 Tool，不需要进入 Registry。一个 Tool 只定义和实现一次，即可被多个中台 Agent 复用。

这套基础完成后，数据中台可以作为第一个真实 Consumer 验证工具契约和数据权限；随后研发中台可以进一步验证长任务、代码执行和隔离模型。运维与安全中台则在长期演进中分别承担运行保障与横向治理职责。

核心原则始终是：

> 少做工具，多证明架构；先完成闭环，再增加复杂度；保持本地开发简单，同时让未来的远程化、团队化和平台化演进有明确路径。
