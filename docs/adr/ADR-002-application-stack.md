# ADR-002：Next.js 与 FastAPI 技术栈

- 状态：Accepted
- 日期：2026-10-01

## 背景

Control Plane 需要类型安全的管理界面；执行侧未来会接入数据、量化和 Agent 生态。

## 决策

Web 使用 Next.js、React 和 TypeScript；API 与执行核心使用 FastAPI 和 Python。前后端使用 REST/OpenAPI 通信。

## 结果

团队需要维护 Node.js 和 Python 两套运行环境，但各自承担其更合适的职责。API 类型后续从 OpenAPI 生成，减少模型漂移。

## 重新评估条件

如果双语言维护成本持续高于生态收益，或执行核心迁移到另一语言，则重新评估。

