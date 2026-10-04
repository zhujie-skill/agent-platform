"use client";

import { useState } from "react";
import type { FormEvent } from "react";

import type { Principal, Tool } from "../lib/types";

type InvokeResult = {
  execution_id: string;
  trace_id: string;
  status: string;
  data: Record<string, unknown>;
  meta: {
    principal: string;
    agent: string;
    tool: string;
    version: string;
    duration_ms: number;
    attempts: number;
    policy_decision: {
      allowed: boolean;
      reason: string;
      required_permissions: string[];
      missing_permissions: string[];
    };
  };
};

function exampleArguments(tool: Tool): string {
  const active = tool.versions.find((version) => version.version === tool.default_version) ?? tool.versions[0];
  const handler = String(active?.executor_config.handler_key ?? "");
  const examples: Record<string, Record<string, unknown>> = {
    "system.echo": { message: "Hello from Phase 3" },
    "sql.list_tables": { schema: "tool_data" },
    "sql.describe_table": { schema: "tool_data", table: "market_prices" },
    "sql.query_readonly": { query: "SELECT 1 AS value", max_rows: 100 },
  };
  if (examples[handler]) return JSON.stringify(examples[handler], null, 2);
  const properties = (active?.input_schema.properties ?? {}) as Record<
    string,
    { type?: string; default?: unknown }
  >;
  const generated = Object.fromEntries(Object.entries(properties).map(([key, schema]) => {
    if (schema.default !== undefined) return [key, schema.default];
    if (key === "symbol") return [key, "AAPL"];
    if (schema.type === "number" || schema.type === "integer") return [key, 1];
    if (schema.type === "boolean") return [key, true];
    return [key, "example"];
  }));
  return JSON.stringify(generated, null, 2);
}

export function ToolPlayground({
  tool,
  principals,
  apiBaseUrl,
}: {
  tool: Tool;
  principals: Principal[];
  apiBaseUrl: string;
}) {
  const consumers = tool.consumer_agents.filter((agent) => agent.binding_enabled);
  const defaultPrincipal =
    principals.find((principal) => principal.external_id === "local-admin") ?? principals[0];
  const [agentId, setAgentId] = useState(consumers[0]?.id ?? "");
  const [principalExternalId, setPrincipalExternalId] = useState(
    defaultPrincipal?.external_id ?? "local-admin",
  );
  const [argumentsText, setArgumentsText] = useState(exampleArguments(tool));
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<InvokeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function invoke(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setResult(null);
    setError(null);
    try {
      const args = JSON.parse(argumentsText) as Record<string, unknown>;
      const response = await fetch(
        `${apiBaseUrl}/api/v1/tools/${tool.namespace}/${tool.name}:invoke`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "X-Local-Principal": principalExternalId,
          },
          body: JSON.stringify({
            arguments: args,
            context: { agent_id: agentId, request_source: "console-playground" },
          }),
        },
      );
      const payload = (await response.json()) as InvokeResult & {
        detail?: { code?: string; message?: string };
      };
      if (!response.ok) {
        const code = payload.detail?.code ? `[${payload.detail.code}] ` : "";
        throw new Error(`${code}${payload.detail?.message ?? `调用失败：HTTP ${response.status}`}`);
      }
      setResult(payload);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "调用失败。");
    } finally {
      setBusy(false);
    }
  }

  if (consumers.length === 0) {
    return <p className="empty-inline">先将此 Tool 绑定给至少一个 Agent，才能从 Playground 调用。</p>;
  }

  return (
    <form className="playground" onSubmit={invoke}>
      <div className="playground-fields">
        <label>
          本地身份
          <select
            onChange={(event) => setPrincipalExternalId(event.target.value)}
            value={principalExternalId}
          >
            {principals.map((principal) => (
              <option key={principal.id} value={principal.external_id}>
                {principal.display_name} · {principal.roles.map((role) => role.name).join(", ")}
              </option>
            ))}
          </select>
        </label>
        <label>
          调用 Agent
          <select onChange={(event) => setAgentId(event.target.value)} value={agentId}>
            {consumers.map((agent) => (
              <option key={agent.id} value={agent.id}>
                {agent.display_name}
              </option>
            ))}
          </select>
        </label>
        <label>
          Arguments JSON
          <textarea
            className="code-input"
            onChange={(event) => setArgumentsText(event.target.value)}
            rows={6}
            value={argumentsText}
          />
        </label>
      </div>
      <button className="button" disabled={busy} type="submit">
        {busy ? "执行中…" : "经过 Policy 调用"}
      </button>
      {error && <div className="result-box result-error">{error}</div>}
      {result && (
        <div className="result-box">
          <div className="result-meta">
            <span>{result.status}</span>
            <span>{result.meta.principal}</span>
            <span>{result.meta.duration_ms} ms</span>
            <span>{result.meta.attempts} attempt(s)</span>
            <span>policy {result.meta.policy_decision.reason}</span>
            <span>execution {result.execution_id.slice(0, 8)}</span>
          </div>
          <pre>{JSON.stringify(result.data, null, 2)}</pre>
        </div>
      )}
    </form>
  );
}
