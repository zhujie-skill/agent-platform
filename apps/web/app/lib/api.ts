import type { ApiResult } from "./types";

export const apiBaseUrl = process.env.API_BASE_URL ?? "http://127.0.0.1:8000";
export const browserApiBaseUrl =
  process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

export async function fetchApi<T>(path: string): Promise<ApiResult<T>> {
  try {
    const response = await fetch(`${apiBaseUrl}${path}`, {
      cache: "no-store",
      signal: AbortSignal.timeout(4_000),
    });
    if (!response.ok) {
      const payload = (await response.json().catch(() => null)) as
        | { detail?: string | { message?: string } }
        | null;
      const detail = payload?.detail;
      const message =
        typeof detail === "string" ? detail : detail?.message ?? `HTTP ${response.status}`;
      return { ok: false, error: message };
    }
    return { ok: true, data: (await response.json()) as T };
  } catch {
    return { ok: false, error: "无法连接本地 Control API。请运行 scripts/dev.ps1。" };
  }
}
