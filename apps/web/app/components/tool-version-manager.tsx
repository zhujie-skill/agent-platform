"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import type { Tool } from "../lib/types";

export function ToolVersionManager({ apiBaseUrl, tool }: { apiBaseUrl: string; tool: Tool }) {
  const router = useRouter();
  const [busy, setBusy] = useState("");
  const [error, setError] = useState("");

  async function mutate(path: string, method: "PATCH" | "POST", body?: object) {
    setBusy(path); setError("");
    try {
      const response = await fetch(`${apiBaseUrl}${path}`, {
        method,
        headers: { "Content-Type": "application/json", "X-Local-Principal": "local-admin" },
        body: body ? JSON.stringify(body) : undefined,
      });
      const payload = await response.json().catch(() => null);
      if (!response.ok) throw new Error(payload?.detail?.message ?? `HTTP ${response.status}`);
      router.refresh();
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "版本操作失败");
    } finally { setBusy(""); }
  }

  return <div className="version-list">
    {tool.versions.map((version) => <div className="version-row" key={version.id}>
      <div><strong>{version.version}</strong><small>{version.executor_type} · {version.registration_channel}</small></div>
      <span className={`status-text ${version.deprecated_at ? "status-failed" : "status-succeeded"}`}>{version.deprecated_at ? "deprecated" : tool.default_version === version.version ? "default" : "available"}</span>
      {!version.deprecated_at && tool.default_version !== version.version && <button className="button button-secondary" disabled={Boolean(busy)} onClick={() => mutate(`/api/v1/tools/${tool.id}`, "PATCH", { default_version: version.version })}>Make default</button>}
      {!version.deprecated_at && tool.default_version !== version.version && <button className="button button-secondary" disabled={Boolean(busy)} onClick={() => mutate(`/api/v1/tools/${tool.id}/versions/${version.version}/deprecate`, "POST")}>Deprecate</button>}
    </div>)}
    {error && <p className="form-message result-error">{error}</p>}
  </div>;
}
