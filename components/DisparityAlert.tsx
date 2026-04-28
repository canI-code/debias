"use client";

import { memo, useMemo, useState } from "react";
import { AlertTriangle, X } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import type { MetricRow } from "@/lib/types";

interface DisparityAlertProps {
  rows: MetricRow[];
}

export const DisparityAlert = memo(function DisparityAlert({ rows }: DisparityAlertProps): JSX.Element | null {
  const [dismissed, setDismissed] = useState(false);

  const flagged = useMemo(() => rows.filter((row) => row.alert_flag).slice(0, 4), [rows]);

  return (
    <AnimatePresence>
      {!dismissed && flagged.length > 0 && (
        <motion.section 
          initial={{ opacity: 0, y: -20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ duration: 0.4, type: "spring", bounce: 0.4 }}
          className="relative overflow-hidden rounded-2xl border border-danger/30 bg-danger/10 p-5 shadow-floating backdrop-blur-md" 
          role="alert" 
          aria-live="assertive"
        >
          {/* Decorative glowing orb in background */}
          <div className="absolute -left-10 -top-10 h-32 w-32 rounded-full bg-danger/20 blur-3xl pointer-events-none" />

          <div className="relative z-10 flex items-start justify-between gap-4">
            <div>
              <h3 className="flex items-center gap-2 text-base font-bold text-danger">
                <AlertTriangle className="h-5 w-5" aria-hidden />
                Disparity Alerts Detected
              </h3>
              <ul className="mt-3 space-y-2 text-sm text-text">
                {flagged.map((row, idx) => (
                  <motion.li 
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 + idx * 0.05 }}
                    key={`${row.group_proxy}-${row.metric_name}`}
                    className="flex items-center gap-2 rounded-lg border border-white/50 bg-white/50 px-3 py-2 shadow-sm transition-transform hover:-translate-y-0.5 hover:shadow-md"
                  >
                    <span className="h-1.5 w-1.5 rounded-full bg-danger" />
                    <span className="font-semibold">{row.metric_name}</span> flagged for <span className="font-medium text-danger">{row.group_proxy}</span> ({row.intersection_key}) with mean {row.mean.toFixed(3)}.
                  </motion.li>
                ))}
              </ul>
            </div>
            <button
              type="button"
              onClick={() => setDismissed(true)}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-danger/10 text-danger transition-colors hover:bg-danger/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-danger"
              aria-label="Dismiss disparity alert"
            >
              <X className="h-4 w-4" aria-hidden />
            </button>
          </div>
        </motion.section>
      )}
    </AnimatePresence>
  );
});
