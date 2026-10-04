"use client";

import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";

export function CreateAgentForm({ apiBaseUrl }: { apiBaseUrl: string }) {
  const router = useRouter();
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setMessage(null);
    const form = new FormData(event.currentTarget);
    const name = String(form.get("name") ?? "").trim();
    const payload = {
      namespace: "platform",
      name,
      display_name: String(form.get("display_name") ?? "").trim(),
      description: String(form.get("description") ?? "").trim(),
      agent_type: String(form.get("agent_type") ?? "custom").trim(),
      owner: String(form.get("owner") ?? "").trim(),
    };
    try {
      const response = await fetch(`${apiBaseUrl}/api/v1/agents`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });
      const result = (await response.json().catch(() => null)) as
        | { detail?: { message?: string } }
        | null;
      if (!response.ok) throw new Error(result?.detail?.message ?? "Agent 创建失败。");
      event.currentTarget.reset();
      setMessage("Agent 已创建。");
      router.refresh();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Agent 创建失败。");
    } finally {
      setBusy(false);
    }
  }

  return (
    <form className="control-form" onSubmit={submit}>
      <div className="form-grid">
        <label>
          显示名称
          <input name="display_name" placeholder="Security Agent" required />
        </label>
        <label>
          唯一名称
          <input name="name" pattern="[a-z0-9][a-z0-9_-]*" placeholder="security-agent" required />
        </label>
        <label>
          类型
          <input name="agent_type" placeholder="security" required />
        </label>
        <label>
          Owner
          <input name="owner" placeholder="Security Platform" required />
        </label>
      </div>
      <label>
        说明
        <textarea name="description" placeholder="说明这个 Agent 的职责。" required rows={3} />
      </label>
      <div className="form-actions">
        <button className="button" disabled={busy} type="submit">
          {busy ? "创建中…" : "创建 Agent"}
        </button>
        {message && <span className="form-message">{message}</span>}
      </div>
    </form>
  );
}
