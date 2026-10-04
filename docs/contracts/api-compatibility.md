# API v1 兼容性承诺

Phase 4 起，`/api/v1` 是数据中台等 Agent runtime 的稳定交接面。

- 已发布的 ToolVersion 不可修改；实现或 schema 变化必须发布新版本。
- v1 可增加可选响应字段，消费方必须忽略未知字段。
- 删除字段、改变字段语义或收紧合法输入需要新的 API family 或 Tool major version。
- discovery 返回的版本和 schema 是该次调用应使用的权威契约。
- 默认版本可以由管理员切换；需要完全可复现的消费者应显式传 `version` 或使用 exact binding。
- 结构化错误的 `detail.code` 可用于程序分支；`message` 只面向人阅读。
- 每次被接受的调用返回 execution/trace 标识；允许、拒绝和失败都会留下审计证据。

机器可读说明位于 `GET /api/v1/compatibility`。

当前 `X-Local-Principal` 仅是本地开发身份适配器。未来切换 OIDC/workload identity 不改变 discovery 和 invoke 的主体数据结构。
