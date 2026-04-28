"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  MessageSquarePlus,
  Trash2,
  MessageSquare,
  Clock,
  ChevronDown,
  ChevronUp,
  AlertTriangle,
} from "lucide-react";
import type { ChatSession } from "@/lib/types";
import { cn } from "@/lib/utils";

interface ChatHistorySidebarProps {
  sessions: ChatSession[];
  activeSessionId: string | null;
  onNewChat: () => void;
  onSwitch: (id: string) => void;
  onDelete: (id: string) => void;
  onDeleteAll: () => void;
}

function formatRelativeTime(ts: number): string {
  const diff = Date.now() - ts;
  const mins = Math.floor(diff / 60_000);
  if (mins < 1) return "just now";
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  return `${days}d ago`;
}

export function ChatHistorySidebar({
  sessions,
  activeSessionId,
  onNewChat,
  onSwitch,
  onDelete,
  onDeleteAll,
}: ChatHistorySidebarProps): JSX.Element {
  const [confirmClearAll, setConfirmClearAll] = useState(false);
  const [collapsed, setCollapsed] = useState(false);

  return (
    <aside className="flex h-full flex-col overflow-hidden" aria-label="Chat history">
      {/* Header */}
      <div className="flex items-center justify-between border-b border-panel-border px-4 py-3">
        <button
          onClick={() => setCollapsed((c) => !c)}
          className="flex items-center gap-2 text-sm font-bold text-text hover:text-accent transition-colors"
        >
          <MessageSquare className="h-4 w-4 text-accent" />
          Chats
          {collapsed ? <ChevronDown className="h-3 w-3 opacity-50" /> : <ChevronUp className="h-3 w-3 opacity-50" />}
        </button>
        <button
          type="button"
          onClick={onNewChat}
          title="New Chat"
          className="flex h-8 w-8 items-center justify-center rounded-xl bg-gradient-to-br from-accent to-purple-400 text-white shadow-floating transition-all duration-300 hover:scale-110 hover:shadow-glass-hover active:scale-95"
        >
          <MessageSquarePlus className="h-4 w-4" />
        </button>
      </div>

      {/* Session List */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="flex-1 overflow-y-auto p-2"
          >
            {sessions.length === 0 ? (
              <div className="flex flex-col items-center justify-center gap-2 py-10 text-center text-xs text-muted">
                <MessageSquare className="h-8 w-8 opacity-30" />
                <p>No chats yet.</p>
                <p className="opacity-70">Click + to start one.</p>
              </div>
            ) : (
              <ul className="space-y-1" role="listbox" aria-label="Chat sessions">
                <AnimatePresence initial={false}>
                  {sessions.map((session, idx) => (
                    <motion.li
                      key={session.id}
                      initial={{ opacity: 0, x: -12 }}
                      animate={{ opacity: 1, x: 0 }}
                      exit={{ opacity: 0, x: -12, height: 0 }}
                      transition={{ delay: idx * 0.02, duration: 0.2 }}
                      role="option"
                      aria-selected={session.id === activeSessionId}
                    >
                      <div
                        className={cn(
                          "group flex cursor-pointer items-start gap-2 rounded-2xl px-3 py-2.5 text-sm transition-all duration-300 hover:-translate-y-0.5 hover:shadow-sm",
                          session.id === activeSessionId
                            ? "bg-accent/10 text-accent ring-1 ring-accent/30"
                            : "text-text hover:bg-white/50 dark:hover:bg-black/30"
                        )}
                        onClick={() => onSwitch(session.id)}
                      >
                        <MessageSquare
                          className={cn(
                            "mt-0.5 h-3.5 w-3.5 shrink-0",
                            session.id === activeSessionId ? "text-accent" : "text-muted"
                          )}
                        />
                        <div className="flex-1 min-w-0">
                          <p className="truncate font-semibold leading-tight">{session.title}</p>
                          <div className="mt-0.5 flex items-center gap-1.5 text-[11px] text-muted">
                            <Clock className="h-3 w-3" />
                            {formatRelativeTime(session.updatedAt)}
                            <span className="opacity-50">·</span>
                            <span>{session.messages.length} msg{session.messages.length !== 1 ? "s" : ""}</span>
                          </div>
                        </div>
                        <button
                          type="button"
                          onClick={(e) => {
                            e.stopPropagation();
                            onDelete(session.id);
                          }}
                          title="Delete chat"
                          className="mt-0.5 shrink-0 rounded-lg p-1 text-muted opacity-0 transition-all group-hover:opacity-100 hover:bg-danger/10 hover:text-danger"
                          aria-label={`Delete chat: ${session.title}`}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </button>
                      </div>
                    </motion.li>
                  ))}
                </AnimatePresence>
              </ul>
            )}
          </motion.div>
        )}
      </AnimatePresence>

      {/* Clear All */}
      {sessions.length > 0 && (
        <div className="border-t border-panel-border p-3">
          <AnimatePresence mode="wait">
            {confirmClearAll ? (
              <motion.div
                key="confirm"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                className="flex flex-col gap-2"
              >
                <p className="flex items-center gap-1.5 text-xs font-semibold text-danger">
                  <AlertTriangle className="h-3.5 w-3.5" />
                  Delete all chats?
                </p>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() => {
                      onDeleteAll();
                      setConfirmClearAll(false);
                    }}
                    className="flex-1 rounded-xl bg-danger px-3 py-1.5 text-xs font-bold text-white transition-transform hover:scale-105 active:scale-95"
                  >
                    Yes, clear all
                  </button>
                  <button
                    type="button"
                    onClick={() => setConfirmClearAll(false)}
                    className="flex-1 rounded-xl border border-panel-border px-3 py-1.5 text-xs font-bold text-text transition-transform hover:scale-105"
                  >
                    Cancel
                  </button>
                </div>
              </motion.div>
            ) : (
              <motion.button
                key="clear"
                initial={{ opacity: 0, y: 4 }}
                animate={{ opacity: 1, y: 0 }}
                exit={{ opacity: 0, y: 4 }}
                type="button"
                onClick={() => setConfirmClearAll(true)}
                className="flex w-full items-center justify-center gap-1.5 rounded-xl border border-danger/30 bg-danger/5 px-3 py-1.5 text-xs font-semibold text-danger transition-all hover:bg-danger/10"
              >
                <Trash2 className="h-3.5 w-3.5" />
                Clear All History
              </motion.button>
            )}
          </AnimatePresence>
        </div>
      )}
    </aside>
  );
}
