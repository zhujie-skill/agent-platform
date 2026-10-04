"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { Agent, McpServer, Tool } from "../lib/types";

type Props = { apiBaseUrl: string; agents: Agent[]; servers: McpServer[] };

async function requestJson<T>(url: string, options: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: { "Content-Type": "application/json", "X-Local-Principal": "local-admin" },
  });
  const payload = await response.json().catch(() => null);
  if (!response.ok) {
    const detail = payload?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message ?? `HTTP ${response.status}`);
  }
  return payload as T;
}

export function McpManager({ apiBaseUrl, agents, servers }: Props) {
  const router = useRouter();
  const [name, setName] = useState("demo-market");
  const [endpoint, setEndpoint] = useState("http://127.0.0.1:8101/mcp");
  const [agentId, setAgentId] = useState(agents[0]?.id ?? "");
  const [busy, setBusy] = useState("");
  const [message, setMessage] = useState("");

  async function run(label: string, action: () => Promise<void>) {
    setBusy(label); setMessage("");
    try { await action(); router.refresh(); }
    catch (error) { setMessage(error instanceof Error ? error.message : "操作失败"); }
    finally { setBusy(""); }
  }

  return (
    <div className="stack">
      <section className="panel section-panel mcp-register">
        <div><p className="eyebrow">EXPLICIT REGISTRATION</p><h2>注册 MCP Server</h2><p className="panel-note">只保存连接元数据；平台不会自动导入或执行远程 Tool。</p></div>
        <div className="inline-form">
          <label>名称<input value={name} onChange={(event) => setName(event.target.value)} /></label>
          <label>Streamable HTTP endpoint<input value={endpoint} onChange={(event) => setEndpoint(event.target.value)} /></label>
          <button className="button" disabled={Boolean(busy)} onClick={() => run("register", async () => {
            await requestJson(`${apiBaseUrl}/api/v1/mcp-servers`, { method: "POST", body: JSON.stringify({ name, endpoint, transport: "streamable_http" }) });
            setMessage("Server 已注册；下一步点击 Discover。");
          })}>{busy === "register" ? "注册中…" : "Register"}</button>
        </div>
        {message && <p className="form-message">{message}</p>}
      </section>

      {servers.map((server) => <article className="tool-card" key={server.id}>
        <div className="tool-header"><div><span className="type-label">{server.transport} · {server.status}</span><h2>{server.name}</h2><p>{server.endpoint}</p></div><button className="button button-secondary" disabled={Boolean(busy)} onClick={() => run(`discover-${server.id}`, async () => { await requestJson(`${apiBaseUrl}/api/v1/mcp-servers/${server.id}/discover`, { method: "POST" }); setMessage("Discovery snapshot 已更新。"); })}>{busy === `discover-${server.id}` ? "Discovering…" : "Discover"}</button></div>
        {server.last_error_safe && <div className="notice notice-error">{server.last_error_safe}</div>}
        <div className="mcp-tools">
          {server.discovery_snapshot.length === 0 ? <p className="empty-inline">尚无快照。启动远端 MCP Server 后点击 Discover。</p> : server.discovery_snapshot.map((tool) => <div className="mcp-tool-row" key={tool.name}>
            <div><span className={`decision decision-${tool.import_state === "changed" ? "error" : "allowed"}`}>{tool.import_state}</span><h3>{tool.title ?? tool.name}</h3><p>{tool.description}</p><code>{tool.name}</code></div>
            <div className="mcp-import">
              <label>绑定给 Agent<select value={agentId} onChange={(event) => setAgentId(event.target.value)}>{agents.map((agent) => <option key={agent.id} value={agent.id}>{agent.display_name}</option>)}</select></label>
              <button className="button" disabled={Boolean(busy) || !agentId} onClick={() => run(`import-${server.id}-${tool.name}`, async () => {
                const imported = await requestJson<Tool>(`${apiBaseUrl}/api/v1/mcp-servers/${server.id}/tools/import`, { method: "POST", body: JSON.stringify({ remote_tool_name: tool.name, namespace: "external", name: tool.name.replaceAll("_", "-"), version: "1.0.0", owner: "External MCP", risk_level: "low", required_permissions: [], make_default: true }) });
                await requestJson(`${apiBaseUrl}/api/v1/agents/${agentId}/tools/${imported.id}`, { method: "PUT", body: JSON.stringify({ version_policy: "default", enabled: true, configuration: {} }) });
                setMessage(`${tool.name} 已导入并绑定。`);
              })}>{busy === `import-${server.id}-${tool.name}` ? "Importing…" : "Import & Bind"}</button>
            </div>
          </div>)}
        </div>
      </article>)}
    </div>
  );
}
