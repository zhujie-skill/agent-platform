# ADR-005：REST/OpenAPI 核心契约与 MCP 适配层

- 状态：Accepted
- 日期：2026-10-01

## 背景

Control Plane、自动化测试和不同 Agent Client 都需要调用工具，但不应让平台核心模型绑定某一种外部协议。

## 决策

平台内部以统一 Tool Contract 和 REST/OpenAPI 为基础。MCP 作为适配层接入，并且所有 MCP 调用仍经过 Tool Gateway。

## 结果

HTTP 调试简单，MCP Client 可以在后续阶段接入，身份、权限、超时和审计不会产生旁路。

## 重新评估条件

如果 MCP 成为唯一且稳定的内部服务协议，或出现无法通过 Adapter 表达的核心语义，再重新评估边界。
