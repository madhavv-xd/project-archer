import type {
  ApiKey,
  CreatedApiKey,
  DashboardStats,
  Model,
  ModelDistribution,
  Paginated,
  RequestLog,
  UsageDaily,
} from "@/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(
  path: string,
  token: string,
  options: RequestInit = {},
): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
      ...options.headers,
    },
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? `Request failed (${res.status})`);
  }
  if (res.status === 204) return undefined as T;
  return res.json();
}

// --- Auth (no token) -------------------------------------------------------

export async function register(input: {
  email: string;
  password: string;
  name?: string;
}): Promise<void> {
  const res = await fetch(`${API_URL}/auth/register`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(input),
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => null);
    throw new Error(detail?.detail ?? "Registration failed");
  }
}

// --- Dashboard (JWT) -------------------------------------------------------

export const api = {
  stats: (token: string) => request<DashboardStats>("/dashboard/stats", token),
  usageDaily: (token: string, days = 30) =>
    request<UsageDaily[]>(`/dashboard/usage-daily?days=${days}`, token),
  modelDistribution: (token: string, days = 30) =>
    request<ModelDistribution[]>(`/dashboard/model-distribution?days=${days}`, token),
  models: (token: string) => request<Model[]>("/models", token),
  logs: (token: string, page = 1, limit = 20) =>
    request<Paginated<RequestLog>>(`/logs?page=${page}&limit=${limit}`, token),
  listKeys: (token: string) => request<ApiKey[]>("/api-keys", token),
  createKey: (token: string, name: string) =>
    request<CreatedApiKey>("/api-keys", token, {
      method: "POST",
      body: JSON.stringify({ name }),
    }),
  deleteKey: (token: string, id: string) =>
    request<void>(`/api-keys/${id}`, token, { method: "DELETE" }),
};
