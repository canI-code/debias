"use client";

import dynamic from "next/dynamic";
import { memo, useMemo } from "react";

import type { MetricRow } from "@/lib/types";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

const RechartsBundle = dynamic(async () => import("./MetricChartRecharts"), {
  ssr: false,
  loading: () => <LoadingSkeleton variant="chart" />
});

interface MetricChartProps {
  rows: MetricRow[];
  metric: "toxicity" | "stereotype_score" | "refusal_prob";
}

export const MetricChart = memo(function MetricChart({ rows, metric }: MetricChartProps): JSX.Element {
  const filtered = useMemo(() => rows.filter((row) => row.metric_name === metric), [rows, metric]);

  if (filtered.length === 0) {
    return (
      <div className="glass flex h-64 flex-col items-center justify-center gap-3 rounded-2xl text-center text-sm text-muted shadow-sm">
        <div className="rounded-full bg-panel-border p-4 opacity-60">
          <svg className="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
        </div>
        <div>
          <p className="font-semibold capitalize text-text">{metric.replace("_", " ")}</p>
          <p className="text-xs mt-1">No data yet — metrics update every 10 s after first chat.</p>
        </div>
      </div>
    );
  }

  return <RechartsBundle rows={filtered} metric={metric} />;
});
