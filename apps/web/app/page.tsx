import Link from "next/link";

import { fetchApi } from "./lib/api";
import type { Agent, DatasourceStatus, MetricsSummary, PlatformHealth } from "./lib/types";

export const dynamic = "force-dynamic";

export default async function Home() {
  const [health, agents, datasource, metrics] = await Promise.all([
    fetchApi<PlatformHealth>("/api/v1/health"),
    fetchApi<Agent[]>("/api/v1/agents"),
    fetchApi<DatasourceStatus>("/api/v1/sql-datasource/status"),
    fetchApi<MetricsSummary>("/api/v1/metrics/summary?hours=24"),
  ]);
  const database = health.ok ? health.data.checks.database : null;
  const summary = metrics.ok ? metrics.data : null;

  return (
    <main>
      <section className="hero hero-compact">
        <div>
          <p className="eyebrow">CONTROL PLANE · PHASE 4</p>
          <h1>Agents choose.<br /><span>Tools execute.</span></h1>
          <p className="subtitle">统一管理 Agent、可复用 Tool、版本、权限和审计；通过 Native、HTTP 与 MCP 执行器连接不同实现。</p>
        </div>
        <div className="overall-status"><span>Platform status</span><span className={`badge badge-${health.ok ? health.data.status : "offline"}`}>{health.ok ? health.data.status : "offline"}</span></div>
      </section>

      <section className="metrics" aria-label="平台指标">
        <Link className="metric" href="/agents"><span>Agents</span><strong>{summary?.total_agents ?? "—"}</strong><small>可见中台 Agent</small></Link>
        <Link className="metric" href="/tools"><span>Active tools</span><strong>{summary?.active_tools ?? "—"}</strong><small>{summary ? `${summary.total_tools} registered` : "Registry"}</small></Link>
        <Link className="metric" href="/executions"><span>24h success</span><strong>{summary ? `${summary.success_rate}%` : "—"}</strong><small>{summary ? `${summary.total_executions} executions` : "No data"}</small></Link>
        <Link className="metric" href="/mcp"><span>Providers</span><strong>{summary ? Object.keys(summary.tools_by_provider).length : "—"}</strong><small>{summary ? Object.entries(summary.tools_by_provider).map(([key, count]) => `${key} ${count}`).join(" · ") : "Native / HTTP / MCP"}</small></Link>
      </section>

      <section className="system-strip">
        <div><span>Metadata PostgreSQL</span><strong className={`badge badge-${database?.status ?? "offline"}`}>{database?.status ?? "offline"}</strong><small>{database?.latency_ms != null ? `${database.latency_ms} ms` : "等待连接"}</small></div>
        <div><span>SQL Tool datasource</span><strong className={`badge badge-${datasource.ok && datasource.data.safely_separated ? "ok" : "unconfigured"}`}>{datasource.ok && datasource.data.safely_separated ? "ready" : "safe closed"}</strong><small>{datasource.ok ? datasource.data.detail : datasource.error}</small></div>
      </section>

      <section className="plane-map">
        <article><p className="eyebrow">CONTROL PLANE</p><h2>定义与治理</h2><p>Agent Catalog、Tool Registry、MCP 导入、版本、绑定、RBAC 与审计。</p></article>
        <span className="plane-arrow">policy-approved contract →</span>
        <article><p className="eyebrow">EXECUTION PLANE</p><h2>隔离与执行</h2><p>Gateway 在运行时选择 Native、HTTP 或 MCP Executor，并记录每次结果。</p></article>
      </section>

      <section className="section-heading"><div><p className="eyebrow">REUSE MAP</p><h2>Agent → Tool</h2></div><Link className="text-link" href="/agents">管理绑定 →</Link></section>
      {!agents.ok ? <div className="notice notice-error">{agents.error}</div> : <section className="reuse-grid">{agents.data.map((agent) => <article className="reuse-card" key={agent.id}><div className="card-heading"><div><span className="type-label">{agent.agent_type}</span><h3>{agent.display_name}</h3></div><span className={`dot dot-${agent.status}`} /></div><p>{agent.description}</p><div className="tool-chain">{agent.tools.length ? agent.tools.map((tool) => <span key={tool.id}>{tool.namespace}.{tool.name}</span>) : <span className="empty-inline">No bound tools</span>}</div></article>)}</section>}
      <footer><span>Local development mode · Phase 4</span><span>{health.ok ? new Date(health.data.timestamp).toLocaleString("zh-CN") : health.error}</span></footer>
    </main>
  );
}
