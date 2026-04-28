"use client";

import Link from "next/link";
import Image from "next/image";
import { useMemo } from "react";
import { motion } from "framer-motion";
import { BarChart3, ChevronLeft, RefreshCw } from "lucide-react";

import { DisparityAlert } from "@/components/DisparityAlert";
import { FairnessTable } from "@/components/FairnessTable";
import { MetricChart } from "@/components/MetricChart";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";
import { useFairnessMetrics } from "@/hooks/useFairnessMetrics";
import { useSettings } from "@/hooks/useSettings";

export default function DashboardPage(): JSX.Element {
  const { data, isLoading, isError, error, refetch } = useFairnessMetrics();
  const { settings } = useSettings();

  const filteredRows = useMemo(
    () =>
      data.filter((row) => {
        if (row.metric_name === "toxicity") {
          return row.mean >= settings.toxicityThreshold;
        }
        if (row.metric_name === "stereotype_score") {
          return row.mean >= settings.stereotypeThreshold;
        }
        if (row.metric_name === "refusal_prob") {
          return row.mean >= settings.refusalThreshold;
        }
        return true;
      }),
    [data, settings]
  );

  return (
    <motion.div 
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="mx-auto grid max-w-7xl gap-6"
    >
      <header className="glass shadow-glass flex flex-wrap items-center justify-between gap-4 rounded-3xl px-8 py-6 transition-all duration-500 hover:-translate-y-1 hover:shadow-glass-hover">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 rounded-full transition-transform hover:scale-105" aria-label="Go home">
            <Image src="/logo.png" alt="DeBias" width={36} height={36} className="drop-shadow-sm" />
            <span className="hidden font-bold text-text sm:inline">DeBias</span>
          </Link>
          <div className="flex items-center gap-3">
            <div className="rounded-xl bg-gradient-to-br from-emerald-400 to-teal-500 p-2 text-white shadow-floating">
              <BarChart3 size={24} />
            </div>
            <div>
              <h1 className="text-2xl font-bold tracking-tight text-text">Fairness Dashboard</h1>
              <p className="text-sm text-muted">Polling every 10 seconds. Live metric tracking.</p>
            </div>
          </div>
        </div>
        <div className="flex items-center gap-3">
          <Link 
            href="/chat" 
            className="rounded-xl border border-white/50 bg-white/40 px-4 py-2.5 text-sm font-semibold text-text shadow-sm backdrop-blur-md transition-all duration-300 hover:-translate-y-0.5 hover:bg-white/60 hover:shadow-glass-hover"
          >
            Back to Chat
          </Link>
          <button
            type="button"
            onClick={() => void refetch()}
            className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-500 to-accent px-4 py-2.5 text-sm font-semibold text-white shadow-floating transition-transform hover:scale-105 active:scale-95"
          >
            <RefreshCw size={16} className={isLoading ? "animate-spin" : ""} />
            <span className="hidden sm:inline">Refresh Data</span>
          </button>
        </div>
      </header>

      <motion.div 
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="grid gap-6"
      >
        <DisparityAlert rows={filteredRows} />

        {isLoading ? <LoadingSkeleton variant="table" /> : null}

        {isError ? (
          <div className="glass flex items-center gap-3 rounded-2xl border-danger/30 bg-danger/5 p-5 text-sm text-danger shadow-sm">
            <div className="rounded-full bg-danger/20 p-2"><BarChart3 size={20} /></div>
            <div>
              <p className="font-semibold">Connection Error</p>
              <p>{error?.message ?? "Could not load metrics. Retrying..."}</p>
            </div>
          </div>
        ) : null}

        {!isLoading && !isError && filteredRows.length === 0 ? (
          <div className="glass rounded-2xl p-8 text-center text-muted shadow-sm">
            <BarChart3 size={48} className="mx-auto mb-4 opacity-20" />
            <p className="text-lg font-medium">No alerts triggered</p>
            <p className="text-sm">No rows meet the selected thresholds yet. Adjust settings or wait for new data.</p>
          </div>
        ) : null}

        <div className="glass shadow-glass overflow-hidden rounded-3xl p-1 transition-all duration-500 hover:shadow-glass-hover">
          <FairnessTable rows={filteredRows} isLoading={isLoading} error={error} />
        </div>

        <div className="grid gap-6 md:grid-cols-1 xl:grid-cols-2">
          <div className="glass shadow-glass rounded-3xl p-6 transition-all duration-500 hover:-translate-y-1 hover:shadow-glass-hover">
            <MetricChart rows={data} metric="toxicity" />
          </div>
          <div className="glass shadow-glass rounded-3xl p-6 transition-all duration-500 hover:-translate-y-1 hover:shadow-glass-hover">
            <MetricChart rows={data} metric="stereotype_score" />
          </div>
        </div>
        
        <div className="glass shadow-glass mb-8 rounded-3xl p-6 transition-all duration-500 hover:-translate-y-1 hover:shadow-glass-hover">
          <MetricChart rows={data} metric="refusal_prob" />
        </div>
      </motion.div>
    </motion.div>
  );
}
