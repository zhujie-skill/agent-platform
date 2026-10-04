import type { Metadata } from "next";

import { BindingManager } from "../components/binding-manager";
import { CreateAgentForm } from "../components/create-agent-form";
import { browserApiBaseUrl, fetchApi } from "../lib/api";
import type { Agent, Tool } from "../lib/types";

export const metadata: Metadata = { title: "Agents" };
export const dynamic = "force-dynamic";

export default async function AgentsPage() {
  const [agents, tools] = await Promise.all([
    fetchApi<Agent[]>("/api/v1/agents"),
    fetchApi<Tool[]>("/api/v1/tools"),
  ]);

  return (
    <main>
      <section className="page-intro">
        <p className="eyebrow">AGENT CATALOG</p>
        <h1>Agents</h1>
        <p className="subtitle">Agent 只会获得已绑定、已启用且通过策略的 Tool。绑定不会复制 Tool 的定义或实现。</p>
      </section>

      {!agents.ok || !tools.ok ? (
        <div className="notice notice-error">{!agents.ok ? agents.error : !tools.ok ? tools.error : ""}</div>
      ) : (
        <section className="stack">
          {agents.data.map((agent) => (
            <article className="catalog-card" key={agent.id}>
              <div className="catalog-main">
                <div className="card-heading">
                  <div><span className="type-label">{agent.namespace}.{agent.name}</span><h2>{agent.display_name}</h2></div>
                  <span className="badge badge-ok">{agent.status}</span>
                </div>
                <p>{agent.description}</p>
                <dl className="compact-dl">
                  <div><dt>Type</dt><dd>{agent.agent_type}</dd></div>
                  <div><dt>Owner</dt><dd>{agent.owner}</dd></div>
                  <div><dt>Bound tools</dt><dd>{agent.tools.length}</dd></div>
                </dl>
              </div>
              <div className="catalog-side">
                <h3>Bound Tools</h3>
                <BindingManager agent={agent} apiBaseUrl={browserApiBaseUrl} tools={tools.data} />
              </div>
            </article>
          ))}
        </section>
      )}

      <section className="panel section-panel">
        <div className="section-heading section-heading-small"><div><p className="eyebrow">CATALOG ACTION</p><h2>创建 Agent 条目</h2></div></div>
        <CreateAgentForm apiBaseUrl={browserApiBaseUrl} />
      </section>
    </main>
  );
}
