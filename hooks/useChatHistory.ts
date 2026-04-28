"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { ChatMessage, ChatSession } from "@/lib/types";

const HISTORY_KEY = "fair-llm-chat-sessions-v1";
const MAX_SESSIONS = 50;

function generateId(): string {
  return crypto.randomUUID();
}

function autoTitle(messages: ChatMessage[]): string {
  const first = messages.find((m) => m.role === "user");
  if (!first) return "New Chat";
  const words = first.content.trim().split(/\s+/).slice(0, 6).join(" ");
  return words.length > 0 ? words : "New Chat";
}

function loadSessions(): ChatSession[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    if (!raw) return [];
    const all = (JSON.parse(raw) as ChatSession[]).slice(0, MAX_SESSIONS);

    // Deduplicate: keep only ONE empty "New Chat" session (the most recent one),
    // discard any others that have no messages — these are phantom sessions from
    // previous page-refresh bugs.
    let keptEmptySession = false;
    const deduped = all.filter((s) => {
      const isEmpty = s.messages.length === 0 && s.title === "New Chat";
      if (isEmpty) {
        if (keptEmptySession) return false; // discard extras
        keptEmptySession = true;
      }
      return true;
    });

    // Persist the cleaned list back so it stays clean
    if (deduped.length !== all.length) {
      localStorage.setItem(HISTORY_KEY, JSON.stringify(deduped));
    }

    return deduped;
  } catch {
    return [];
  }
}

function saveSessions(sessions: ChatSession[]): void {
  localStorage.setItem(HISTORY_KEY, JSON.stringify(sessions.slice(0, MAX_SESSIONS)));
}

interface UseChatHistoryReturn {
  sessions: ChatSession[];
  activeSessionId: string | null;
  activeMessages: ChatMessage[];
  createSession: () => string;
  switchSession: (id: string) => void;
  deleteSession: (id: string) => void;
  deleteAllSessions: () => void;
  updateActiveMessages: (messages: ChatMessage[]) => void;
}

export function useChatHistory(): UseChatHistoryReturn {
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState<string | null>(null);

  // Load sessions on mount — create the first one only if storage is truly empty
  useEffect(() => {
    const loaded = loadSessions();
    if (loaded.length > 0) {
      setSessions(loaded);
      setActiveSessionId(loaded[0].id);
    } else {
      // First ever visit — create one default session and persist it
      const firstSession: ChatSession = {
        id: generateId(),
        title: "New Chat",
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      saveSessions([firstSession]);
      setSessions([firstSession]);
      setActiveSessionId(firstSession.id);
    }
  }, []);

  const createSession = useCallback((): string => {
    const newSession: ChatSession = {
      id: generateId(),
      title: "New Chat",
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    setSessions((prev) => {
      const updated = [newSession, ...prev];
      saveSessions(updated);
      return updated;
    });
    setActiveSessionId(newSession.id);
    return newSession.id;
  }, []);

  const switchSession = useCallback((id: string) => {
    setActiveSessionId(id);
  }, []);

  const deleteSession = useCallback(
    (id: string) => {
      setSessions((prev) => {
        const updated = prev.filter((s) => s.id !== id);
        saveSessions(updated);
        return updated;
      });
      setActiveSessionId((current) => {
        if (current !== id) return current;
        // Switch to the next available session
        const remaining = sessions.filter((s) => s.id !== id);
        return remaining.length > 0 ? remaining[0].id : null;
      });
    },
    [sessions]
  );

  const deleteAllSessions = useCallback(() => {
    setSessions([]);
    setActiveSessionId(null);
    localStorage.removeItem(HISTORY_KEY);
  }, []);

  const updateActiveMessages = useCallback((messages: ChatMessage[]) => {
    setSessions((prev) => {
      const updated = prev.map((s) => {
        if (s.id !== activeSessionId) return s;
        return {
          ...s,
          messages,
          title: autoTitle(messages) || s.title,
          updatedAt: Date.now(),
        };
      });
      saveSessions(updated);
      return updated;
    });
  }, [activeSessionId]);

  const activeMessages = useMemo(() => {
    const session = sessions.find((s) => s.id === activeSessionId);
    return session?.messages ?? [];
  }, [sessions, activeSessionId]);

  return {
    sessions,
    activeSessionId,
    activeMessages,
    createSession,
    switchSession,
    deleteSession,
    deleteAllSessions,
    updateActiveMessages,
  };
}
