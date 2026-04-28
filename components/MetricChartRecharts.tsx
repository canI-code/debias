"use client";

import { useMemo } from "react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis
} from "recharts";

import type { MetricRow } from "@/lib/types";
import { formatCI } from "@/lib/utils";

interface MetricChartRechartsProps {
  rows: MetricRow[];
  metric: "toxicity" | "stereotype_score" | "refusal_prob";
}

const palette = ["#2271D8", "#0FA78D", "#D95F59", "#CF8500", "#7A6CF5", "#27826F"];

export default function MetricChartRecharts({ rows, metric }: MetricChartRechartsProps): JSX.Element {
  const chartData = useMemo(
    () =>
      rows.map((row, index) => ({
        group: row.group_proxy,
        mean: row.mean,
        ci: formatCI(row.ci_low, row.ci_high),
        confidenceLow: row.ci_low,
        confidenceHigh: row.ci_high,
        color: palette[index % palette.length]
      })),
    [rows]
  );

  return (
    <section className="glass rounded-3xl p-6 shadow-floating" aria-label={`${metric} chart`}>
      <header className="mb-6">
        <h3 className="text-xl font-bold capitalize text-text">{metric.replace("_", " ")} By Group</h3>
        <p className="text-sm text-muted">Distribution visualization</p>
      </header>
      
      <div className="grid gap-6 lg:grid-cols-2">
        <div className="relative h-[300px] rounded-2xl border border-white/40 bg-white/30 p-4 shadow-inner-glow backdrop-blur-md">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 24 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} strokeOpacity={0.2} />
              <XAxis dataKey="group" interval={0} angle={-18} height={45} textAnchor="end" tick={{ fontSize: 11, fill: 'currentColor', opacity: 0.7 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: 'currentColor', opacity: 0.7 }} axisLine={false} tickLine={false} />
              <Tooltip 
                formatter={(value: number) => value.toFixed(3)} 
                labelFormatter={(label) => `Group: ${label}`}
                contentStyle={{ borderRadius: '12px', border: '1px solid var(--panel-border)', background: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(12px)' }} 
              />
              <Bar dataKey="mean" radius={[6, 6, 0, 0]} barSize={32}>
                {chartData.map((entry) => (
                  <Cell key={entry.group} fill={entry.color} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="relative h-[300px] rounded-2xl border border-white/40 bg-white/30 p-4 shadow-inner-glow backdrop-blur-md">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={chartData} margin={{ top: 8, right: 8, left: -20, bottom: 24 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} strokeOpacity={0.2} />
              <XAxis dataKey="group" interval={0} angle={-18} height={45} textAnchor="end" tick={{ fontSize: 11, fill: 'currentColor', opacity: 0.7 }} axisLine={false} tickLine={false} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 11, fill: 'currentColor', opacity: 0.7 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{ borderRadius: '12px', border: '1px solid var(--panel-border)', background: 'rgba(255, 255, 255, 0.8)', backdropFilter: 'blur(12px)' }}
                formatter={(value: number, key: string) => {
                  if (key === "mean") {
                    return value.toFixed(3);
                  }
                  return value?.toString() ?? "N/A";
                }}
              />
              <Line type="monotone" dataKey="mean" stroke="#2271D8" strokeWidth={3} dot={{ r: 5, strokeWidth: 2, fill: "#fff" }} activeDot={{ r: 7 }} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </section>
  );
}
