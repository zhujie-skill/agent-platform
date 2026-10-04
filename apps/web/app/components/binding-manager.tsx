"use client";

import { useRouter } from "next/navigation";
import { useMemo, useState } from "react";

import type { Agent, Tool } from "../lib/types";

type Props = {
  agent: Agent;
  tools: Tool[];
  apiBaseUrl: string;
};

export function BindingManager({ agent, tools, apiBaseUrl }: Props) {
  const router = useRouter();
  const boundIds = useMemo(() => new Set(agent.tools.map((tool) => tool.id)), [agent.tools]);
  const available = tools.filter((tool) => !boundIds.has(tool.id));
  const [selectedToolId, setSelectedToolId] = useState(available[0]?.id ?? "");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function bindTool() {
    if (!selectedToolId) return;
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/v1/agents/${agent.id}/tools/${selectedToolId}`,
        {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ version_policy: "default", enabled: true }),
        },
      );
      if (!response.ok) throw new Error("绑定失败，请查看 API 日志。");
      setMessage("Tool 已绑定。界面正在刷新。");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "绑定失败。");
    } finally {
      setBusy(false);
    }
  }

  async function unbindTool(toolId: string) {
    setBusy(true);
    setMessage(null);
    try {
      const response = await fetch(
        `${apiBaseUrl}/api/v1/agents/${agent.id}/tools/${toolId}`,
        { method: "DELETE" },
      );
      if (!response.ok) throw new Error("解除绑定失败，请查看 API 日志。");
      setMessage("绑定已解除。界面正在刷新。");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "解除绑定失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="binding-manager">
      <div className="binding-list">
        {agent.tools.length === 0 ? (
          <span className="empty-inline">尚未绑定 Tool</span>
        ) : (
          agent.tools.map((tool) => (
            <span className="binding-chip" key={tool.id}>
              {tool.namespace}.{tool.name}
              <button disabled={busy} onClick={() => unbindTool(tool.id)} type="button">
                ×
              </button>
            </span>
          ))
        )}
      </div>
      {available.length > 0 && (
        <div className="inline-form">
          <select
            aria-label={`为 ${agent.display_name} 选择 Tool`}
            onChange={(event) => setSelectedToolId(event.target.value)}
            value={selectedToolId}
          >
            {available.map((tool) => (
              <option key={tool.id} value={tool.id}>
                {tool.namespace}.{tool.name}
              </option>
            ))}
          </select>
          <button className="button button-secondary" disabled={busy} onClick={bindTool} type="button">
            绑定 Tool
          </button>
        </div>
      )}
      {message && <p className="form-message">{message}</p>}
    </div>
  );
}
