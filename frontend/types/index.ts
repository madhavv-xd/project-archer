export interface ApiKey {
  id: string;
  name: string;
  key_prefix: string;
  is_active: boolean;
  created_at: string;
  last_used_at: string | null;
}

export interface CreatedApiKey {
  id: string;
  name: string;
  key: string;
  prefix: string;
}

export interface Model {
  id: string;
  name: string;
  display_name: string;
  provider: string;
  model_id: string;
  is_active: boolean;
  context_window: number;
  speed_tier: string;
  best_for: string[];
}

export interface RequestLog {
  id: string;
  model: string | null;
  routing_reason: string;
  prompt_tokens: number | null;
  completion_tokens: number | null;
  total_tokens: number | null;
  latency_ms: number;
  status: string;
  fallback_used: boolean;
  created_at: string;
}

export interface Paginated<T> {
  items: T[];
  page: number;
  limit: number;
  total: number;
  total_pages: number;
}

export interface DashboardStats {
  total_requests: number;
  requests_today: number;
  total_tokens: number;
  success_rate: number;
  most_used_model: string | null;
}
