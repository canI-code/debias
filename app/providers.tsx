"use client";

import { type ReactNode, useEffect, useMemo, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

interface ProvidersProps {
  children: ReactNode;
}

function ThemeProvider({ children }: { children: ReactNode }): JSX.Element {
  const [darkMode, setDarkMode] = useState<boolean>(false);

  useEffect(() => {
    const stored = localStorage.getItem("fair-llm-settings-v2");
    if (stored) {
      try {
        const parsed = JSON.parse(stored) as { darkMode?: boolean };
        setDarkMode(Boolean(parsed.darkMode));
      } catch {
        setDarkMode(window.matchMedia("(prefers-color-scheme: dark)").matches);
      }
    } else {
      setDarkMode(window.matchMedia("(prefers-color-scheme: dark)").matches);
    }
  }, []);

  useEffect(() => {
    document.documentElement.dataset.theme = darkMode ? "dark" : "light";
    if (darkMode) {
      document.documentElement.classList.add("dark");
    } else {
      document.documentElement.classList.remove("dark");
    }
  }, [darkMode]);

  return <>{children}</>;
}

export function Providers({ children }: ProvidersProps): JSX.Element {
  const queryClient = useMemo(
    () =>
      new QueryClient({
        defaultOptions: {
          queries: {
            retry: 3,
            retryDelay: (attempt) => Math.min(1000 * 2 ** attempt, 10_000)
          }
        }
      }),
    []
  );

  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>{children}</ThemeProvider>
    </QueryClientProvider>
  );
}
