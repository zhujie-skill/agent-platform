import type { Metadata } from "next";

import { fetchApi } from "../lib/api";
import type { Execution } from "../lib/types";

export const metadata: Metadata = { title: "Executions" };
export const dynamic = "force-dynamic";

export default async function ExecutionsPage() {
  const executions = await fetchApi<Execution[]>("/api/v1/executions?limit=100");

  return (
    <main>
      <section className="page-intro">
        <p className="eyebrow">EXECUTION PLANE</p><h1>Executions</h1>
        <p className="subtitle">每次调用都会保留身份、策略决策、重试次数、最终版本和 trace_id；成功与拒绝都可解释。</p>
      </section>

      {!executions.ok ? <div className="notice notice-error">{executions.error}</div> : executions.data.length === 0 ? (
        <div className="notice">还没有执行记录。前往 Tools 页面运行一次 Playground。</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Status</th><th>Principal</th><th>Agent</th><th>Tool</th><th>Policy</th><th>Attempts</th><th>Duration</th><th>Started</th><th>Trace</th></tr></thead>
            <tbody>{executions.data.map((execution) => (
              <tr key={execution.id}>
                <td><span className={`status-text status-${execution.status}`}>{execution.status}</span>{execution.error_code && <small>{execution.error_code}</small>}</td>
                <td>{execution.principal_name ?? "—"}</td><td>{execution.agent_name}</td><td><code>{execution.tool_name}</code><small>v{execution.tool_version}</small></td>
                <td><span className={`decision decision-${execution.policy_decision?.allowed ? "allowed" : "denied"}`}>{execution.policy_decision?.allowed ? "allowed" : "denied"}</span>{execution.policy_decision?.missing_permissions.length ? <small>missing: {execution.policy_decision.missing_permissions.join(", ")}</small> : null}</td>
                <td>{execution.attempts}</td><td>{execution.duration_ms != null ? `${execution.duration_ms} ms` : "—"}</td><td>{new Date(execution.started_at).toLocaleString("zh-CN")}</td>
                <td><code title={execution.trace_id}>{execution.trace_id.slice(0, 8)}</code></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </main>
  );
}
