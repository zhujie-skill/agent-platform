import type { Metadata } from "next";

import { fetchApi } from "../lib/api";
import type { Permission, Principal, Role } from "../lib/types";

export const metadata: Metadata = { title: "Policies" };
export const dynamic = "force-dynamic";

export default async function PoliciesPage() {
  const [principals, roles, permissions] = await Promise.all([
    fetchApi<Principal[]>("/api/v1/principals"),
    fetchApi<Role[]>("/api/v1/roles"),
    fetchApi<Permission[]>("/api/v1/permissions"),
  ]);
  const failed = !principals.ok || !roles.ok || !permissions.ok;

  return (
    <main>
      <section className="page-intro">
        <p className="eyebrow">IDENTITY · RBAC · RISK</p><h1>Policies</h1>
        <p className="subtitle">Agent 绑定决定“可以发现哪些 Tool”，身份权限决定“这次能否调用”。最终授权是两者的交集。</p>
      </section>

      <section className="policy-explainer">
        <div><span>1</span><strong>Agent binding</strong><p>所选 Agent 必须显式绑定该 Tool。</p></div>
        <div><span>2</span><strong>Principal permissions</strong><p>请求身份必须拥有版本要求和风险等级要求的全部权限。</p></div>
        <div><span>3</span><strong>Runtime guardrails</strong><p>Schema、只读事务、超时、行数和脱敏继续限制实际执行。</p></div>
      </section>

      {failed ? (
        <div className="notice notice-error">治理数据暂时不可用，请确认 API 和数据库已启动。</div>
      ) : (
        <>
          <section className="section-heading">
            <div><p className="eyebrow">LOCAL IDENTITY PROVIDER</p><h2>Principals</h2></div>
            <span className="phase">X-Local-Principal</span>
          </section>
          <section className="policy-grid">
            {principals.data.map((principal) => (
              <article className="policy-card" key={principal.id}>
                <div className="card-heading"><div><span className="type-label">{principal.type}</span><h3>{principal.display_name}</h3></div><span className={`dot dot-${principal.status}`} /></div>
                <code>{principal.external_id}</code>
                {principal.agent_name && <p>Scoped Agent: <code>{principal.agent_name}</code></p>}
                <p>Roles: {principal.roles.map((role) => role.name).join(", ") || "none"}</p>
                <div className="permission-list">
                  {principal.permissions.map((permission) => <span key={permission}>{permission}</span>)}
                </div>
              </article>
            ))}
          </section>

          <section className="section-heading spaced-heading">
            <div><p className="eyebrow">ROLE MATRIX</p><h2>Roles & permissions</h2></div>
            <span className="phase">{permissions.data.length} permissions</span>
          </section>
          <section className="policy-grid">
            {roles.data.map((role) => (
              <article className="policy-card" key={role.id}>
                <div><span className="type-label">ROLE</span><h3>{role.name}</h3></div>
                <p>{role.description}</p>
                <div className="permission-list">
                  {role.permissions.map((permission) => <span title={permission.description} key={permission.id}>{permission.key}</span>)}
                </div>
                <small>Assigned to: {role.principals.map((principal) => principal.display_name).join(", ") || "nobody"}</small>
              </article>
            ))}
          </section>
        </>
      )}
    </main>
  );
}
