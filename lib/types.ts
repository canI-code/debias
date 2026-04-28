export interface MetricRow {
  group_proxy: string;
  intersection_key: string;
  metric_name: string;
  mean: number;
  std: number;
  count: number;
  ci_low: number | null;
  ci_high: number | null;
  alert_flag: boolean;
  low_confidence: boolean;
  computed_at: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  timestamp: number;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
}

export interface Settings {
  toxicityThreshold: number;
  stereotypeThreshold: number;
  refusalThreshold: number;
  darkMode: boolean;
}

export interface MetricsResponse {
  request_id: string | null;
  page: number;
  page_size: number;
  total: number;
  stale: boolean;
  generated_at: string;
  rows: MetricRow[];
  metadata: Record<string, { definition: string; harm_context: string; limitations: string }>;
  trade_off_note: string;
}

export interface HealthResponse {
  status: "ok" | "degraded";
  db: boolean;
  redis: boolean;
  llm: boolean;
  worker_lag_seconds: number | null;
  stale: boolean;
  queue_depth: number;
  request_id: string;
  details: Record<string, unknown>;
}
