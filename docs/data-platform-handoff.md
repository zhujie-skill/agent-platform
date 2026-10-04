# 数据中台接入工具中台

此文档只定义两个中台之间的边界，不设计数据中台内部架构。

## 身份

`data-agent-runtime` 是 `service_account`，拥有 `data-analyst` 角色，并绑定到 `platform.data-agent`。Gateway 会拒绝它代表任何其他 Agent 发现或执行 Tool。

本地请求使用：

```text
X-Local-Principal: data-agent-runtime
```

生产环境必须替换为不可伪造的 workload identity；不能把该本地 header 当成生产认证。

## 标准调用流程

1. `GET /api/v1/compatibility` 检查 API family。
2. `GET /api/v1/agents/{data_agent_id}/available-tools` 获取当下获授权 Tool 和 input schema。
3. 根据 discovery 返回的完整 Tool 名称调用 `POST /api/v1/tools/{namespace}/{name}:invoke`。
4. 保存 `execution_id` 与 `trace_id`，用于故障排查和评测证据。
5. 业务层只读取返回数据，不直接获得 SQL 数据库连接串。

## 运行示例

先保持 `scripts/dev.ps1` 运行并执行 `scripts/seed-demo.ps1`，然后：

```powershell
.\.venv\Scripts\python.exe .\examples\data_platform_consumer.py
```

示例会以 service account 发现 SQL Tool、列举 `tool_data` 表并只读查询演示行情。
