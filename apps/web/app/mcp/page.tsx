import type { Metadata } from "next";

import { McpManager } from "../components/mcp-manager";
import { browserApiBaseUrl, fetchApi } from "../lib/api";
import type { Agent, McpServer } from "../lib/types";

export const metadata: Metadata = { title: "MCP" };
export const dynamic = "force-dynamic";

export default async function McpPage() {
  const [servers, agents] = await Promise.all([
    fetchApi<McpServer[]>("/api/v1/mcp-servers"),
    fetchApi<Agent[]>("/api/v1/agents"),
  ]);
  return <main>
    <section className="page-intro"><p className="eyebrow">MCP CONTROL PLANE</p><h1>External MCP</h1><p className="subtitle">注册连接、显式发现、审查 schema，再导入为版本化平台 Tool。远端实现保持独立，平台统一负责绑定、权限、执行记录和审计。</p></section>
    {!servers.ok ? <div className="notice notice-error">{servers.error}</div> : !agents.ok ? <div className="notice notice-error">{agents.error}</div> : <McpManager apiBaseUrl={browserApiBaseUrl} agents={agents.data} servers={servers.data} />}
  </main>;
}
