export type HealthCheck = {
  status: "ok" | "unconfigured" | "error";
  configured?: boolean | null;
  latency_ms?: number | null;
  detail?: string | null;
};

export type PlatformHealth = {
  status: "ok" | "degraded";
  service: string;
  version: string;
  environment: string;
  timestamp: string;
  checks: { api: HealthCheck; database: HealthCheck };
};

export type ToolReference = {
  id: string;
  namespace: string;
  name: string;
  display_name: string;
  provider_type: string;
  status: string;
  version_policy: string;
  binding_enabled: boolean;
};

export type AgentReference = {
  id: string;
  namespace: string;
  name: string;
  display_name: string;
  status: string;
  version_policy: string;
  binding_enabled: boolean;
};

export type Agent = {
  id: string;
  namespace: string;
  name: string;
  display_name: string;
  description: string;
  agent_type: string;
  status: string;
  owner: string;
  created_at: string;
  tools: ToolReference[];
};

export type ToolVersion = {
  id: string;
  version: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown>;
  executor_type: string;
  executor_config: Record<string, unknown>;
  timeout_seconds: number;
  retry_policy: Record<string, unknown>;
  required_permissions: string[];
  definition_hash: string;
  registration_channel: string;
  created_at: string;
  deprecated_at: string | null;
};

export type Tool = {
  id: string;
  namespace: string;
  name: string;
  display_name: string;
  description: string;
  owner: string;
  provider_type: string;
  risk_level: string;
  status: string;
  default_version: string | null;
  created_at: string;
  versions: ToolVersion[];
  consumer_agents: AgentReference[];
};

export type Execution = {
  id: string;
  trace_id: string;
  status: string;
  agent_id: string;
  agent_name: string;
  principal_id: string | null;
  principal_name: string | null;
  tool_id: string;
  tool_name: string;
  tool_version: string;
  request_source: string;
  error_code: string | null;
  error_message_safe: string | null;
  started_at: string;
  finished_at: string | null;
  duration_ms: number | null;
  attempts: number;
  policy_decision: {
    allowed: boolean;
    reason: string;
    risk_level: string;
    required_permissions: string[];
    granted_permissions: string[];
    missing_permissions: string[];
  } | null;
};

export type RoleReference = { id: string; name: string; description: string };
export type PrincipalReference = { id: string; display_name: string; external_id: string };

export type Principal = {
  id: string;
  type: string;
  display_name: string;
  external_id: string;
  status: string;
  agent_id: string | null;
  agent_name: string | null;
  roles: RoleReference[];
  permissions: string[];
};

export type Permission = { id: string; key: string; description: string };

export type Role = {
  id: string;
  name: string;
  description: string;
  permissions: Permission[];
  principals: PrincipalReference[];
};

export type AuditEvent = {
  id: string;
  actor_principal_id: string | null;
  actor_name: string | null;
  action: string;
  resource_type: string;
  resource_id: string;
  decision: string;
  metadata_redacted: Record<string, unknown>;
  trace_id: string;
  created_at: string;
};

export type DatasourceStatus = {
  configured: boolean;
  safely_separated: boolean;
  allowed_schemas: string[];
  statement_timeout_ms: number;
  max_rows: number;
  detail: string;
};

export type DiscoveredMcpTool = {
  name: string;
  title: string | null;
  description: string;
  input_schema: Record<string, unknown>;
  output_schema: Record<string, unknown> | null;
  import_state: "new" | "unchanged" | "changed";
};

export type McpServer = {
  id: string;
  name: string;
  transport: string;
  endpoint: string;
  auth_secret_ref: string | null;
  status: string;
  discovery_snapshot: DiscoveredMcpTool[];
  last_discovered_at: string | null;
  last_error_safe: string | null;
  created_at: string;
};

export type MetricsSummary = {
  window_hours: number;
  total_agents: number;
  total_tools: number;
  active_tools: number;
  total_executions: number;
  succeeded_executions: number;
  failed_executions: number;
  success_rate: number;
  average_duration_ms: number | null;
  tools_by_provider: Record<string, number>;
  tools_by_risk: Record<string, number>;
  executions_by_status: Record<string, number>;
};

export type ApiResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: string };
