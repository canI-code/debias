import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]): string {
  return twMerge(clsx(inputs));
}

export function formatCI(low: number | null, high: number | null): string {
  if (low === null || high === null || Number.isNaN(low) || Number.isNaN(high)) {
    return "N/A";
  }
  return `${low.toFixed(3)} - ${high.toFixed(3)}`;
}

export function parseSSEChunk(chunk: string): string {
  const lines = chunk.split("\n");
  const dataLines = lines.filter((line) => line.startsWith("data:"));
  return dataLines.map((line) => line.replace(/^data:\s?/, "")).join("\n");
}

export function sanitizeForDisplay(text: string): string {
  const stripped = text.replace(/[\u0000-\u001F\u007F-\u009F]/g, "").trim();
  if (stripped.length <= 12000) {
    return stripped;
  }
  return `${stripped.slice(0, 12000)}…`;
}

export function mergeChatText(previous: string, chunk: string): string {
  const cleanedChunk = chunk.replace(/[\u0000-\u001F\u007F-\u009F]/g, "");
  if (!cleanedChunk) {
    return previous;
  }
  if (!previous) {
    return cleanedChunk;
  }

  const previousEndsWithWord = /[\p{L}\p{N}]$/u.test(previous);
  const chunkStartsWithWord = /^[\p{L}\p{N}]/u.test(cleanedChunk);
  if (previousEndsWithWord && chunkStartsWithWord && !/^\s/.test(cleanedChunk)) {
    return `${previous} ${cleanedChunk}`;
  }

  return `${previous}${cleanedChunk}`;
}
