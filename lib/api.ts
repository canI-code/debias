import axios, { AxiosError, AxiosInstance, AxiosRequestConfig, AxiosResponse } from "axios";
import { z } from "zod";

import type { HealthResponse, MetricRow, MetricsResponse } from "@/lib/types";

const runtimeBaseUrl = process.env.NEXT_PUBLIC_API_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL;
const API_BASE = runtimeBaseUrl || "http://localhost:8000";

if (process.env.NODE_ENV === "production" && !runtimeBaseUrl) {
  console.warn(
    "[fair-llm] NEXT_PUBLIC_API_URL is not set. " +
      "Set it to your backend API origin in Vercel project settings (Environment Variables)."
  );
}

const MetricRowSchema = z.object({
  group_proxy: z.string(),
  intersection_key: z.string(),
  metric_name: z.string(),
  mean: z.number(),
  std: z.number(),
  count: z.number(),
  ci_low: z.number().nullable(),
  ci_high: z.number().nullable(),
  alert_flag: z.boolean(),
  low_confidence: z.boolean(),
  computed_at: z.string(),
  // Extra fields the backend includes — passthrough so they don't fail validation
  definition: z.string().optional(),
  harm_context: z.string().optional(),
  limitations: z.string().optional(),
});

const MetricsResponseSchema = z.object({
  request_id: z.string().nullable().optional(),
  page: z.number(),
  page_size: z.number(),
  total: z.number(),
  stale: z.boolean(),
  generated_at: z.string(),
  // Backend returns "items"; frontend also supports "rows" for forward-compat
  items: z.array(MetricRowSchema).optional(),
  rows: z.array(MetricRowSchema).optional(),
  metadata: z.record(
    z.object({
      definition: z.string(),
      harm_context: z.string(),
      limitations: z.string()
    })
  ).optional(),
  trade_off_note: z.string().optional()
});

const ChatRequestSchema = z.object({
  message: z.string().min(1)
});

const ChatResponseSchema = z.object({
  request_id: z.string(),
  response_text: z.string(),
  model: z.string(),
  status: z.string(),
  latency_ms: z.number(),
  queued_for_fairness: z.boolean()
});

const HealthSchema = z.object({
  status: z.union([z.literal("ok"), z.literal("degraded")]),
  db: z.boolean(),
  redis: z.boolean(),
  llm: z.boolean(),
  worker_lag_seconds: z.number().nullable(),
  stale: z.boolean(),
  queue_depth: z.number(),
  request_id: z.string(),
  details: z.record(z.unknown())
});

interface AxiosRetryConfig extends AxiosRequestConfig {
  _retryCount?: number;
}

function sleep(durationMs: number): Promise<void> {
  return new Promise((resolve) => {
    globalThis.setTimeout(resolve, durationMs);
  });
}

export const api: AxiosInstance = axios.create({
  baseURL: API_BASE,
  timeout: 10_000
});

api.interceptors.response.use(
  (response: AxiosResponse) => response,
  async (error: AxiosError) => {
    const config = (error.config ?? {}) as AxiosRetryConfig;
    config._retryCount = config._retryCount ?? 0;

    if (config._retryCount >= 3) {
      return Promise.reject(error);
    }

    config._retryCount += 1;
    const backoff = 200 * 2 ** (config._retryCount - 1);
    const jitter = Math.floor(Math.random() * 120);
    await sleep(backoff + jitter);
    return api.request(config);
  }
);

export function mapApiError(error: unknown): string {
  if (error instanceof AxiosError) {
    if (error.code === "ECONNABORTED") {
      return "The server took too long to respond. Please try again.";
    }
    if (error.response?.status === 404) {
      return "The requested endpoint is unavailable.";
    }
    if (error.response?.status === 429) {
      return "Rate limit reached. Please wait before retrying.";
    }
    if (error.response?.status && error.response.status >= 500) {
      return "The server encountered an error. Try again shortly.";
    }
    return "Network request failed. Check your connection and retry.";
  }
  if (error instanceof z.ZodError) {
    return "Received data in an unexpected format.";
  }
  return "An unknown error occurred.";
}

export async function postChat(message: string): Promise<{ response_text: string }> {
  const payload = ChatRequestSchema.parse({ message });
  const response = await api.post("/chat", payload);
  return ChatResponseSchema.parse(response.data);
}

export async function getMetrics(): Promise<MetricsResponse> {
  const response = await api.get("/metrics");
  const parsed = MetricsResponseSchema.parse(response.data);
  const resolvedRows: MetricRow[] = parsed.rows ?? parsed.items ?? [];


  return {
    request_id: parsed.request_id ?? null,
    page: parsed.page,
    page_size: parsed.page_size,
    total: parsed.total,
    stale: parsed.stale,
    generated_at: parsed.generated_at,
    rows: resolvedRows,
    metadata: parsed.metadata ?? {},
    trade_off_note: parsed.trade_off_note ?? ""
  };
}

export async function getHealth(): Promise<HealthResponse> {
  const response = await api.get("/health");
  return HealthSchema.parse(response.data) as HealthResponse;
}

export {
  ChatRequestSchema,
  HealthSchema,
  MetricRowSchema,
  MetricsResponseSchema
};
