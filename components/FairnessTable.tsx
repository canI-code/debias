"use client";

import { memo, useMemo, useState } from "react";
import { AlertTriangle, ChevronLeft, ChevronRight, ArrowUpDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import { formatCI } from "@/lib/utils";
import type { MetricRow } from "@/lib/types";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

type SortableKey = keyof Pick<MetricRow, "group_proxy" | "metric_name" | "mean" | "count" | "computed_at">;

interface FairnessTableProps {
  rows: MetricRow[];
  isLoading: boolean;
  error: Error | null;
}

function nextDirection(current: "asc" | "desc"): "asc" | "desc" {
  return current === "asc" ? "desc" : "asc";
}

export const FairnessTable = memo(function FairnessTable({ rows, isLoading, error }: FairnessTableProps): JSX.Element {
  const [sortBy, setSortBy] = useState<SortableKey>("computed_at");
  const [direction, setDirection] = useState<"asc" | "desc">("desc");
  const [page, setPage] = useState<number>(1);

  const pageSize = 8;

  const sortedRows = useMemo(() => {
    const cloned = [...rows];
    cloned.sort((left, right) => {
      const leftValue = left[sortBy];
      const rightValue = right[sortBy];

      if (typeof leftValue === "number" && typeof rightValue === "number") {
        return direction === "asc" ? leftValue - rightValue : rightValue - leftValue;
      }

      return direction === "asc"
        ? String(leftValue).localeCompare(String(rightValue))
        : String(rightValue).localeCompare(String(leftValue));
    });
    return cloned;
  }, [rows, sortBy, direction]);

  const paginatedRows = useMemo(() => {
    const start = (page - 1) * pageSize;
    return sortedRows.slice(start, start + pageSize);
  }, [sortedRows, page]);

  const pageCount = Math.max(1, Math.ceil(sortedRows.length / pageSize));

  const onHeaderClick = (key: SortableKey): void => {
    if (key === sortBy) {
      setDirection((current) => nextDirection(current));
      return;
    }
    setSortBy(key);
    setDirection("asc");
  };

  if (isLoading) {
    return <LoadingSkeleton variant="table" />;
  }

  if (error) {
    return (
      <div className="rounded-2xl border border-danger/40 bg-danger/10 p-6 text-sm text-danger shadow-floating backdrop-blur-md">
        <div className="flex items-center gap-2 font-semibold">
          <AlertTriangle className="h-5 w-5" />
          Error loading fairness metrics
        </div>
        <p className="mt-2 text-danger/80">{error.message}</p>
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="glass flex h-64 flex-col items-center justify-center rounded-2xl p-6 text-center text-sm text-muted shadow-sm">
        <div className="mb-3 rounded-full bg-panel-border p-4">
          <AlertTriangle className="h-6 w-6 opacity-50" />
        </div>
        <p className="font-medium text-text">No fairness data available yet.</p>
        <p className="mt-1">Waiting for initial background job to complete.</p>
      </div>
    );
  }

  return (
    <section className="glass rounded-3xl p-6 shadow-floating" aria-label="Fairness distribution table">
      <div className="mb-6 flex items-center justify-between">
        <h2 className="text-xl font-bold text-text">Distribution Metrics</h2>
        <span className="rounded-full bg-accent/10 px-3 py-1 text-xs font-semibold text-accent">
          {rows.length} Total Signals
        </span>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-white/40 bg-white/30 shadow-inner-glow backdrop-blur-md">
        <table className="min-w-full text-left text-sm text-text">
          <thead className="border-b border-panel-border bg-white/40 backdrop-blur-sm">
            <tr className="text-xs font-bold uppercase tracking-wider text-muted">
              {["group_proxy", "metric_name", "mean", "count", "computed_at"].map((key) => {
                const typedKey = key as SortableKey;
                const isActive = sortBy === typedKey;
                return (
                  <th key={key} scope="col" className="p-4" aria-sort={isActive ? (direction === "asc" ? "ascending" : "descending") : "none"}>
                    <button
                      type="button"
                      onClick={() => onHeaderClick(typedKey)}
                      className="group flex items-center gap-1.5 transition-colors hover:text-accent focus:outline-none"
                    >
                      {key.replace("_", " ")}
                      <ArrowUpDown className={`h-3.5 w-3.5 transition-transform ${isActive ? "text-accent" : "opacity-0 group-hover:opacity-50"}`} />
                    </button>
                  </th>
                );
              })}
              <th scope="col" className="p-4 font-bold">Confidence (CI)</th>
              <th scope="col" className="p-4 font-bold text-right">Status Flags</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-panel-border">
            <AnimatePresence mode="popLayout">
              {paginatedRows.map((row, idx) => (
                <motion.tr 
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0 }}
                  transition={{ delay: idx * 0.03, duration: 0.2 }}
                  key={`${row.group_proxy}-${row.intersection_key}-${row.metric_name}`} 
                  className="transition-colors duration-300 hover:bg-white/60"
                >
                  <td className="p-4 font-medium">{row.group_proxy}</td>
                  <td className="p-4">
                    <span className="rounded-md border border-white/50 bg-white/50 px-2 py-1 text-xs shadow-sm">{row.metric_name}</span>
                  </td>
                  <td className="p-4 font-mono font-medium">{row.mean.toFixed(3)}</td>
                  <td className="p-4">{row.count}</td>
                  <td className="p-4 text-xs text-muted">{new Date(row.computed_at).toLocaleString([], { dateStyle: 'short', timeStyle: 'short' })}</td>
                  <td className="p-4 font-mono text-xs">{formatCI(row.ci_low, row.ci_high)}</td>
                  <td className="p-4 text-right">
                    <div className="flex items-center justify-end gap-2">
                      {row.alert_flag ? (
                        <span className="inline-flex rounded-full bg-danger px-2.5 py-0.5 text-[11px] font-bold tracking-wide text-white shadow-sm">ALERT</span>
                      ) : (
                        <span className="inline-flex rounded-full bg-success/20 px-2.5 py-0.5 text-[11px] font-bold tracking-wide text-success">OK</span>
                      )}
                      {row.low_confidence ? (
                        <span className="inline-flex items-center gap-1 rounded-full bg-warning/20 px-2 py-0.5 text-[11px] font-bold text-warning" title="Low sample size">
                          <AlertTriangle className="h-3 w-3" />
                          LOW N
                        </span>
                      ) : null}
                    </div>
                  </td>
                </motion.tr>
              ))}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      <div className="mt-6 flex items-center justify-between">
        <p className="text-sm font-medium text-muted">
          Showing <span className="text-text">{(page - 1) * pageSize + 1}</span> to <span className="text-text">{Math.min(page * pageSize, sortedRows.length)}</span> of <span className="text-text">{sortedRows.length}</span> results
        </p>
        <div className="flex gap-2">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-panel-border text-text transition-all hover:scale-105 active:scale-95 disabled:pointer-events-none disabled:opacity-40"
            aria-label="Previous page"
          >
            <ChevronLeft className="h-5 w-5" />
          </button>
          <button
            type="button"
            disabled={page >= pageCount}
            onClick={() => setPage((current) => Math.min(pageCount, current + 1))}
            className="flex h-9 w-9 items-center justify-center rounded-xl bg-panel-border text-text transition-all hover:scale-105 active:scale-95 disabled:pointer-events-none disabled:opacity-40"
            aria-label="Next page"
          >
            <ChevronRight className="h-5 w-5" />
          </button>
        </div>
      </div>
    </section>
  );
});
