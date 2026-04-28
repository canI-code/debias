"use client";

import { useEffect, useState } from "react";
import { useQuery, type UseQueryResult } from "@tanstack/react-query";

import { getMetrics, mapApiError } from "@/lib/api";
import type { MetricRow } from "@/lib/types";

interface FairnessMetricsResult {
  data: MetricRow[];
  isLoading: boolean;
  isError: boolean;
  error: Error | null;
  refetch: () => Promise<unknown>;
}

export function useFairnessMetrics(): FairnessMetricsResult {
  const [isTabVisible, setIsTabVisible] = useState<boolean>(true);

  useEffect(() => {
    const listener = (): void => {
      setIsTabVisible(document.visibilityState === "visible");
    };
    document.addEventListener("visibilitychange", listener);
    return () => {
      document.removeEventListener("visibilitychange", listener);
    };
  }, []);

  const query: UseQueryResult<MetricRow[], Error> = useQuery({
    queryKey: ["metrics"],
    queryFn: async () => {
      const metrics = await getMetrics();
      return metrics.rows;
    },
    refetchInterval: isTabVisible ? 5_000 : false,
    staleTime: 3_000,
    // Don't retry on 400/4xx — those are config errors, not transient failures
    retry: (failureCount, error) => {
      if (error instanceof Error && error.message.includes("400")) return false;
      return failureCount < 2;
    },
    retryDelay: (attempt) => Math.min(2000 * 2 ** attempt, 15_000),
    select: (data) => data
  });

  const queryError = query.error ? new Error(mapApiError(query.error)) : null;

  return {
    data: query.data ?? [],
    isLoading: query.isLoading,
    isError: query.isError,
    error: queryError,
    refetch: async () => query.refetch()
  };
}
