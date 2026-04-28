"use client";

import { useId } from "react";
import { SlidersHorizontal, Settings2 } from "lucide-react";

import type { Settings } from "@/lib/types";

interface SettingsPanelProps {
  settings: Settings;
  onChange: (settings: Partial<Settings>) => void;
  onReset: () => void;
}

function SliderField(props: {
  label: string;
  value: number;
  onChange: (value: number) => void;
  id: string;
}): JSX.Element {
  return (
    <div className="glass rounded-2xl p-4 shadow-sm transition-all duration-300 hover:-translate-y-1 hover:bg-white/40 hover:shadow-glass-hover dark:hover:bg-black/30">
      <label htmlFor={props.id} className="mb-2 flex items-center justify-between text-sm font-semibold text-text">
        <span>{props.label}</span>
        <span className="rounded-lg bg-accent/10 px-2 py-0.5 text-accent">{props.value.toFixed(2)}</span>
      </label>
      <input
        id={props.id}
        type="range"
        min={0}
        max={1}
        step={0.01}
        value={props.value}
        onChange={(event) => props.onChange(Number(event.target.value))}
        aria-valuemin={0}
        aria-valuemax={1}
        aria-valuenow={props.value}
        className="h-1.5 w-full appearance-none rounded-full bg-panel-border outline-none transition-all [&::-webkit-slider-thumb]:h-4 [&::-webkit-slider-thumb]:w-4 [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-accent [&::-webkit-slider-thumb]:shadow-md [&::-webkit-slider-thumb]:transition-transform hover:[&::-webkit-slider-thumb]:scale-125"
      />
    </div>
  );
}

export function SettingsPanel({ settings, onChange, onReset }: SettingsPanelProps): JSX.Element {
  const toxicityId = useId();
  const stereotypeId = useId();
  const refusalId = useId();

  return (
    <aside className="p-1" aria-label="Settings drawer">
      <header className="mb-6 flex items-center gap-3 px-2">
        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-gradient-to-tr from-accent to-blue-400 text-white shadow-floating transition-transform duration-300 hover:scale-110 hover:shadow-glass-hover">
          <Settings2 aria-hidden className="h-5 w-5" />
        </div>
        <div>
          <h2 className="text-lg font-bold text-text">Settings</h2>
          <p className="text-xs text-muted">Tune dashboard thresholds</p>
        </div>
      </header>

      <div className="space-y-4">
        <SliderField
          id={toxicityId}
          label="Toxicity threshold"
          value={settings.toxicityThreshold}
          onChange={(value) => onChange({ toxicityThreshold: value })}
        />
        <SliderField
          id={stereotypeId}
          label="Stereotype threshold"
          value={settings.stereotypeThreshold}
          onChange={(value) => onChange({ stereotypeThreshold: value })}
        />
        <SliderField
          id={refusalId}
          label="Refusal threshold"
          value={settings.refusalThreshold}
          onChange={(value) => onChange({ refusalThreshold: value })}
        />


        <button
          type="button"
          onClick={onReset}
          className="w-full rounded-2xl border border-white/50 bg-white/40 px-4 py-3 text-sm font-bold text-text shadow-sm transition-all duration-300 hover:-translate-y-1 hover:bg-white/60 hover:shadow-glass-hover active:scale-95"
        >
          Reset Defaults
        </button>
      </div>
    </aside>
  );
}
