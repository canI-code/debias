"use client";

import { memo, useEffect, useMemo, useRef, useState } from "react";
import { AlertCircle, LoaderCircle, RotateCcw, Send, Sparkles } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

import type { ChatMessage } from "@/lib/types";
import { cn, sanitizeForDisplay } from "@/lib/utils";
import { LoadingSkeleton } from "@/components/LoadingSkeleton";

interface ChatWindowProps {
  onSend: (msg: string) => void;
  messages: ChatMessage[];
  isStreaming: boolean;
  error?: string | null;
  onRetry?: () => void;
}

function renderMarkdownLike(text: string): JSX.Element {
  const parts = text.split(/(\*\*[^*]+\*\*|`[^`]+`)/g);
  return (
    <>
      {parts.map((part, index) => {
        if (part.startsWith("**") && part.endsWith("**")) {
          return <strong key={index}>{part.slice(2, -2)}</strong>;
        }
        if (part.startsWith("`") && part.endsWith("`")) {
          return (
            <code key={index} className="rounded-md bg-black/10 px-1.5 py-0.5 text-[0.9em] font-medium shadow-inner-glow backdrop-blur-sm dark:bg-white/10">
              {part.slice(1, -1)}
            </code>
          );
        }
        return <span key={index}>{part}</span>;
      })}
    </>
  );
}

const MessageBubble = memo(function MessageBubble({ message }: { message: ChatMessage }): JSX.Element {
  const isAssistant = message.role === "assistant";

  return (
    <motion.article
      initial={{ opacity: 0, y: 10, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ duration: 0.3, ease: "easeOut" }}
      className={cn(
        "max-w-[85%] rounded-3xl px-5 py-4 text-[15px] leading-relaxed shadow-sm",
        isAssistant 
          ? "glass rounded-tl-sm text-text" 
          : "ml-auto bg-gradient-to-br from-accent to-blue-500 rounded-tr-sm text-white shadow-floating"
      )}
      aria-label={`${message.role} message`}
    >
      <p className="whitespace-pre-wrap break-words">{renderMarkdownLike(sanitizeForDisplay(message.content))}</p>
      <time className={cn("mt-2 block text-xs font-medium", isAssistant ? "text-muted" : "text-blue-100")}>
        {new Date(message.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
      </time>
    </motion.article>
  );
});

export function ChatWindow({ onSend, messages, isStreaming, error = null, onRetry }: ChatWindowProps): JSX.Element {
  const [draft, setDraft] = useState("");
  const [showAll, setShowAll] = useState(false);
  const viewportRef = useRef<HTMLDivElement | null>(null);

  const renderedMessages = useMemo(() => {
    if (showAll || messages.length <= 50) {
      return messages;
    }
    return messages.slice(-50);
  }, [messages, showAll]);

  useEffect(() => {
    viewportRef.current?.scrollTo({ top: viewportRef.current.scrollHeight, behavior: "smooth" });
  }, [renderedMessages, isStreaming]);

  const handleSubmit = (): void => {
    const trimmed = draft.trim();
    if (!trimmed || isStreaming) {
      return;
    }
    onSend(trimmed);
    setDraft("");
  };

  const onKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>): void => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      handleSubmit();
    }
  };

  return (
    <section className="flex h-[calc(100vh-12rem)] flex-col bg-transparent" aria-label="Chat window">
      <header className="glass relative z-10 border-b border-panel-border p-4 shadow-sm transition-all duration-500 hover:scale-[1.01] hover:shadow-glass-hover">
        <div className="flex items-center gap-2">
          <Sparkles className="h-5 w-5 text-accent" />
          <h1 className="text-lg font-bold text-text">Bias-mitigated assistant</h1>
        </div>
        <p className="text-xs text-muted mt-1">Press Enter to send. Shift+Enter for new line.</p>
      </header>

      {messages.length === 0 ? (
        <div className="p-6">
          <LoadingSkeleton variant="chat" />
        </div>
      ) : null}

      {messages.length > 50 && !showAll ? (
        <div className="px-6 pt-4 text-center">
          <button
            type="button"
            onClick={() => setShowAll(true)}
            className="rounded-full border border-panel-border bg-panel-glass px-4 py-1.5 text-xs font-semibold text-text shadow-sm transition-all hover:scale-105"
          >
            Load older messages ({messages.length - 50})
          </button>
        </div>
      ) : null}

      <AnimatePresence>
        {error ? (
          <motion.div 
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            className="mx-4 mt-4 overflow-hidden"
          >
            <div className="flex items-center justify-between rounded-2xl border border-danger/30 bg-danger/10 px-4 py-3 text-sm text-danger shadow-sm" role="status" aria-live="polite">
              <span className="inline-flex items-center gap-2 font-medium">
                <AlertCircle className="h-5 w-5" aria-hidden />
                {error}
              </span>
              {onRetry ? (
                <button type="button" onClick={onRetry} className="inline-flex items-center gap-1.5 rounded-lg bg-danger/20 px-3 py-1.5 font-semibold transition-colors hover:bg-danger/30">
                  <RotateCcw className="h-4 w-4" aria-hidden /> Retry
                </button>
              ) : null}
            </div>
          </motion.div>
        ) : null}
      </AnimatePresence>

      <div ref={viewportRef} className="flex-1 space-y-6 overflow-y-auto p-6 scroll-smooth" tabIndex={0} aria-label="Conversation history">
        {renderedMessages.map((message) => (
          <MessageBubble key={message.id} message={message} />
        ))}
        {isStreaming ? (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            className="glass inline-flex items-center gap-3 rounded-full px-4 py-2 text-sm font-medium text-muted shadow-sm" aria-live="polite"
          >
            <LoaderCircle className="h-4 w-4 animate-spin text-accent" aria-hidden />
            Analyzing & responding...
          </motion.div>
        ) : null}
      </div>

      <footer className="glass relative z-10 border-t border-panel-border p-4 shadow-[0_-4px_20px_rgba(0,0,0,0.05)] transition-all duration-500 hover:-translate-y-1 hover:shadow-glass-hover">
        <label htmlFor="chat-input" className="sr-only">
          Message input
        </label>
        <div className="relative flex items-end gap-3 rounded-3xl border border-white/50 bg-white/40 p-2 shadow-inner-glow backdrop-blur-md transition-all duration-300 focus-within:-translate-y-1 focus-within:bg-white/60 focus-within:shadow-glass-hover focus-within:ring-2 focus-within:ring-accent/50">
          <textarea
            id="chat-input"
            value={draft}
            onChange={(event) => setDraft(event.target.value)}
            onKeyDown={onKeyDown}
            rows={Math.min(4, draft.split("\n").length || 1)}
            placeholder="Type your message..."
            className="max-h-32 w-full resize-none bg-transparent px-4 py-3 text-[15px] text-text placeholder:text-muted focus:outline-none"
            aria-label="Type your message"
          />
          <button
            type="button"
            onClick={handleSubmit}
            disabled={isStreaming || draft.trim().length === 0}
            className="flex h-12 w-12 shrink-0 items-center justify-center rounded-2xl bg-gradient-to-br from-accent to-blue-500 text-white shadow-floating transition-transform hover:scale-105 active:scale-95 disabled:pointer-events-none disabled:opacity-40"
          >
            <Send className="h-5 w-5" aria-hidden />
          </button>
        </div>
      </footer>
    </section>
  );
}
