"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

const defaultInputSchema = JSON.stringify(
  {
    type: "object",
    additionalProperties: false,
    required: ["message"],
    properties: { message: { type: "string", minLength: 1 } },
  },
  null,
  2,
);

const defaultOutputSchema = JSON.stringify(
  {
    type: "object",
    additionalProperties: false,
    required: ["message"],
    properties: { message: { type: "string" } },
  },
  null,
  2,
);

export function RegisterToolForm({ apiBaseUrl }: { apiBaseUrl: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    try {
      const payload = {
        namespace: String(form.get("namespace") ?? "").trim(),
        name: String(form.get("name") ?? "").trim(),
        display_name: String(form.get("display_name") ?? "").trim(),
        description: String(form.get("description") ?? "").trim(),
        owner: String(form.get("owner") ?? "").trim(),
        provider_type: "native",
        risk_level: String(form.get("risk_level") ?? "low"),
        version: {
          version: String(form.get("version") ?? "1.0.0").trim(),
          handler_key: String(form.get("handler_key") ?? "system.echo").trim(),
          input_schema: JSON.parse(String(form.get("input_schema"))),
          output_schema: JSON.parse(String(form.get("output_schema"))),
          registration_channel: "console",
          make_default: true,
        },
      };
      const response = await fetch(`${apiBaseUrl}/api/v1/tools`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json().catch(() => null)) as
        | { detail?: { message?: string } }
        | null;
      if (!response.ok) throw new Error(result?.detail?.message ?? "Tool 注册失败。");
      event.currentTarget.reset();
      setMessage("Tool 已注册。请前往 Agents 页面建立绑定。");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Tool 注册失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="control-form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          Namespace
          <input defaultValue="system" name="namespace" pattern="[a-z0-9][a-z0-9_-]*" required />
        </label>
        <label>
          唯一名称
          <input name="name" pattern="[a-z0-9][a-z0-9_-]*" placeholder="echo-demo" required />
        </label>
        <label>
          显示名称
          <input name="display_name" placeholder="Echo Demo" required />
        </label>
        <label>
          Owner
          <input defaultValue="Tool Platform" name="owner" required />
        </label>
        <label>
          Version
          <input defaultValue="1.0.0" name="version" pattern="\d+\.\d+\.\d+" required />
        </label>
        <label>
          Risk
          <select defaultValue="low" name="risk_level">
            <option value="low">low</option>
            <option value="medium">medium</option>
            <option value="high">high</option>
          </select>
        </label>
        <label>
          Native handler
          <select defaultValue="system.echo" name="handler_key">
            <option value="system.echo">system.echo</option>
          </select>
        </label>
      </div>
      <label>
        说明
        <textarea name="description" placeholder="说明该 Tool 的能力与边界。" required rows={3} />
      </label>
      <details>
        <summary>JSON Schema</summary>
        <div className="schema-editors">
          <label>
            Input schema
            <textarea className="code-input" defaultValue={defaultInputSchema} name="input_schema" rows={12} />
          </label>
          <label>
            Output schema
            <textarea className="code-input" defaultValue={defaultOutputSchema} name="output_schema" rows={12} />
          </label>
        </div>
      </details>
      <div className="form-actions">
        <button className="button" disabled={busy} type="submit">
          {busy ? "注册中…" : "注册原生 Tool"}
        </button>
        {message && <span className="form-message">{message}</span>}
      </div>
    </form>
  );
}
