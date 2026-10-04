# ADR-001：Control Plane 与 Execution Plane 分层

- 状态：Accepted
- 日期：2026-10-01

## 背景

平台既要管理工具定义、版本、权限和审计，也要处理真实工具调用。若两类职责混在工具实现中，后续迁移到远程 Worker 或接入安全中台时会产生大量重复逻辑。

## 决策

将工具中台划分为 Control Plane 和 Execution Plane。Control Plane 管理工具及策略，Execution Plane 通过统一 Gateway 完成身份解析、Schema 校验、策略判断、执行路由和结果标准化。

## 结果

首版可以共用一个 FastAPI 进程，但代码边界和数据契约必须保持分离。未来拆进程不改变调用方契约。

## 重新评估条件

如果平台只保留静态工具目录而完全不负责执行，则重新评估 Execution Plane 的归属。

