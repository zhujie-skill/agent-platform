# ADR-003：云 PostgreSQL 与厂商中立

- 状态：Accepted
- 日期：2026-10-01

## 背景

应用当前只在本地运行，但控制面元数据需要跨本地会话持久保存。

## 决策

使用云端托管 PostgreSQL，通过标准 `DATABASE_URL`、SQLAlchemy 和 Alembic 接入。不在核心代码中使用特定供应商 SDK。

## 结果

Neon、Supabase、AWS RDS 等兼容服务均可使用。连接凭证只通过环境变量注入；未配置数据库时应用以 degraded 模式启动。

## 重新评估条件

如果平台需要离线运行、区域合规或数据库特有能力，再评估本地副本或供应商扩展。

