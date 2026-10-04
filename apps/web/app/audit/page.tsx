import type { Metadata } from "next";

import { fetchApi } from "../lib/api";
import type { AuditEvent } from "../lib/types";

export const metadata: Metadata = { title: "Audit" };
export const dynamic = "force-dynamic";

export default async function AuditPage() {
  const events = await fetchApi<AuditEvent[]>("/api/v1/audit-events?limit=200");

  return (
    <main>
      <section className="page-intro">
        <p className="eyebrow">IMMUTABLE EXPLANATION TRAIL</p><h1>Audit</h1>
        <p className="subtitle">记录谁、何时、对什么资源做了什么，以及策略允许、拒绝或执行出错。敏感参数不会进入审计元数据。</p>
      </section>

      {!events.ok ? <div className="notice notice-error">{events.error}</div> : events.data.length === 0 ? (
        <div className="notice">还没有审计事件。前往 Tools 以不同身份执行一次 Tool。</div>
      ) : (
        <div className="table-wrap">
          <table>
            <thead><tr><th>Decision</th><th>Action</th><th>Actor</th><th>Resource</th><th>When</th><th>Trace</th><th>Explanation</th></tr></thead>
            <tbody>{events.data.map((event) => (
              <tr key={event.id}>
                <td><span className={`decision decision-${event.decision}`}>{event.decision}</span></td>
                <td><code>{event.action}</code></td>
                <td>{event.actor_name ?? "system"}</td>
                <td>{event.resource_type}<small>{event.resource_id.slice(0, 8)}</small></td>
                <td>{new Date(event.created_at).toLocaleString("zh-CN")}</td>
                <td><code title={event.trace_id}>{event.trace_id.slice(0, 8)}</code></td>
                <td><details className="audit-details"><summary>查看安全元数据</summary><pre>{JSON.stringify(event.metadata_redacted, null, 2)}</pre></details></td>
              </tr>
            ))}</tbody>
          </table>
        </div>
      )}
    </main>
  );
}
