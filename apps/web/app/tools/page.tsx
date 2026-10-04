import type { Metadata } from "next";

import { RegisterToolForm } from "../components/register-tool-form";
import { ToolPlayground } from "../components/tool-playground";
import { ToolVersionManager } from "../components/tool-version-manager";
import { browserApiBaseUrl, fetchApi } from "../lib/api";
import type { DatasourceStatus, Principal, Tool } from "../lib/types";

export const metadata: Metadata = { title: "Tools" };
export const dynamic = "force-dynamic";

export default async function ToolsPage() {
  const [tools, principals, datasource] = await Promise.all([
    fetchApi<Tool[]>("/api/v1/tools"),
    fetchApi<Principal[]>("/api/v1/principals"),
    fetchApi<DatasourceStatus>("/api/v1/sql-datasource/status"),
  ]);

  return <main>
    <section className="page-intro"><p className="eyebrow">TOOL REGISTRY</p><h1>Tools</h1><p className="subtitle">统一展示 Native、HTTP 与 MCP Tool。每个版本不可变；Agent 绑定和身份权限共同决定能否调用。</p></section>
    {datasource.ok && <section className={`datasource-banner ${datasource.data.safely_separated ? "datasource-ready" : "datasource-warn"}`}><div><p className="eyebrow">READ-ONLY SQL DATASOURCE</p><strong>{datasource.data.safely_separated ? "已安全配置" : "未就绪（安全关闭）"}</strong><p>{datasource.data.detail}</p></div><dl className="compact-dl"><div><dt>Schemas</dt><dd>{datasource.data.allowed_schemas.join(", ")}</dd></div><div><dt>Timeout</dt><dd>{datasource.data.statement_timeout_ms} ms</dd></div><div><dt>Max rows</dt><dd>{datasource.data.max_rows}</dd></div></dl></section>}
    {!tools.ok ? <div className="notice notice-error">{tools.error}</div> : <section className="stack">{tools.data.map((tool) => {
      const active = tool.versions.find((version) => version.version === tool.default_version) ?? tool.versions[0];
      return <article className="tool-card" key={tool.id}>
        <div className="tool-header"><div><span className="type-label">{tool.provider_type} · {tool.risk_level} risk · {tool.status}</span><h2>{tool.namespace}.{tool.name}</h2><p>{tool.description}</p></div><div className="tool-version"><span>default</span><strong>{tool.default_version ?? "—"}</strong></div></div>
        <div className="tool-layout"><div><h3>Consumers</h3><div className="binding-list">{tool.consumer_agents.length ? tool.consumer_agents.map((agent) => <span className="binding-chip static" key={agent.id}>{agent.display_name}</span>) : <span className="empty-inline">No Agent bindings</span>}</div><h3>Contract</h3><dl className="compact-dl"><div><dt>Owner</dt><dd>{tool.owner}</dd></div><div><dt>Executor</dt><dd>{active?.executor_type ?? "—"}</dd></div><div><dt>Timeout</dt><dd>{active ? `${active.timeout_seconds}s` : "—"}</dd></div><div><dt>Permissions</dt><dd>{active?.required_permissions.join(", ") || "tool.invoke"}</dd></div></dl>{active && <details className="schema-details"><summary>查看 Input Schema</summary><pre>{JSON.stringify(active.input_schema, null, 2)}</pre></details>}<h3 className="spaced-heading">Versions</h3><ToolVersionManager apiBaseUrl={browserApiBaseUrl} tool={tool} /></div><div><h3>Playground</h3>{principals.ok ? <ToolPlayground apiBaseUrl={browserApiBaseUrl} principals={principals.data} tool={tool} /> : <div className="notice notice-error">{principals.error}</div>}</div></div>
      </article>;
    })}</section>}
    <section className="panel section-panel"><div className="section-heading section-heading-small"><div><p className="eyebrow">NATIVE REGISTRATION</p><h2>注册平台原生 Tool</h2></div></div><p className="panel-note">演示表单只开放已经部署的安全 handler。HTTP 与 MCP 使用各自受控的注册流程。</p><RegisterToolForm apiBaseUrl={browserApiBaseUrl} /></section>
  </main>;
}
