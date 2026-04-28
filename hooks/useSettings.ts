"use client";

import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { z } from "zod";

import type { Settings } from "@/lib/types";

const SETTINGS_KEY = "fair-llm-settings-v2";

const SettingsSchema = z.object({
  toxicityThreshold: z.number().min(0).max(1),
  stereotypeThreshold: z.number().min(0).max(1),
  refusalThreshold: z.number().min(0).max(1),
  darkMode: z.boolean()
});

const defaults: Settings = {
  toxicityThreshold: 0.15,
  stereotypeThreshold: 0.15,
  refusalThreshold: 0.2,
  darkMode: false
};

function migrateLegacy(input: unknown): Settings {
  const legacySchema = z.object({
    toxicity: z.number().optional(),
    stereotype: z.number().optional(),
    refusal: z.number().optional(),
    theme: z.union([z.literal("light"), z.literal("dark")]).optional()
  });

  const parsed = legacySchema.safeParse(input);
  if (!parsed.success) {
    return defaults;
  }

  return {
    toxicityThreshold: parsed.data.toxicity ?? defaults.toxicityThreshold,
    stereotypeThreshold: parsed.data.stereotype ?? defaults.stereotypeThreshold,
    refusalThreshold: parsed.data.refusal ?? defaults.refusalThreshold,
    darkMode: parsed.data.theme === "dark"
  };
}

export function useSettings(): {
  settings: Settings;
  updateSettings: (partial: Partial<Settings>) => void;
  resetSettings: () => void;
} {
  const [settings, setSettings] = useState<Settings>(defaults);
  const writeTimer = useRef<number | null>(null);

  useEffect(() => {
    const raw = localStorage.getItem(SETTINGS_KEY);
    if (!raw) {
      return;
    }

    try {
      const parsedJson: unknown = JSON.parse(raw);
      const parsedSettings = SettingsSchema.safeParse(parsedJson);
      if (parsedSettings.success) {
        setSettings(parsedSettings.data);
        return;
      }
      setSettings(migrateLegacy(parsedJson));
    } catch {
      setSettings(defaults);
    }
  }, []);

  useEffect(() => {
    if (writeTimer.current !== null) {
      window.clearTimeout(writeTimer.current);
    }

    writeTimer.current = window.setTimeout(() => {
      localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
      if (typeof document !== "undefined") {
        document.documentElement.dataset.theme = settings.darkMode ? "dark" : "light";
        if (settings.darkMode) {
          document.documentElement.classList.add("dark");
        } else {
          document.documentElement.classList.remove("dark");
        }
      }
    }, 180);

    return () => {
      if (writeTimer.current !== null) {
        window.clearTimeout(writeTimer.current);
      }
    };
  }, [settings]);

  const updateSettings = useCallback((partial: Partial<Settings>) => {
    setSettings((current) => {
      const merged = { ...current, ...partial };
      const validated = SettingsSchema.safeParse(merged);
      return validated.success ? validated.data : current;
    });
  }, []);

  const resetSettings = useCallback(() => {
    setSettings(defaults);
  }, []);

  return useMemo(
    () => ({
      settings,
      updateSettings,
      resetSettings
    }),
    [settings, updateSettings, resetSettings]
  );
}
