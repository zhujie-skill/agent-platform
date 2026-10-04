# Phase 3 演示脚本

准备：完成迁移，运行 `scripts/dev.ps1`，再运行 `scripts/seed-demo.ps1`。

1. Overview（1 分钟）：解释 Control Plane / Execution Plane；展示 provider 与成功率指标。
2. Agents（1 分钟）：Data、Developer、Operations、Security 只是消费者，同一 Tool 可被多个 Agent 绑定。
3. Tools（2 分钟）：分别调用 `system.echo`、`http.health_check`、`external.market-snapshot`，强调统一 invoke 契约。
4. MCP（2 分钟）：展示 Server 是连接登记；Discovery 是远端快照；Import 才是显式、版本化的平台登记。
5. Policies / Executions / Audit（1 分钟）：解释一次允许或拒绝决策，以及 trace_id 如何串联证据。
6. Platform MCP（1 分钟）：运行 `scripts/verify_phase3.py`，证明标准 MCP Client 能发现并调用平台已授权 Tool。

演示后可在 Neon SQL Editor 查看 `executions` 和 `audit_events`；参数与敏感结果按策略脱敏，不应出现数据库密码。
