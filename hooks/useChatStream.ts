"use client";

import { useCallback, useMemo, useRef, useState } from "react";

import { mapApiError, postChat } from "@/lib/api";
import { mergeChatText, sanitizeForDisplay } from "@/lib/utils";
import type { ChatMessage } from "@/lib/types";

interface HookState {
  messages: ChatMessage[];
  isStreaming: boolean;
  error: string | null;
  sendMessage: (message: string) => Promise<void>;
  abort: () => void;
  clearMessages: () => void;
}

interface UseChatStreamOptions {
  messages: ChatMessage[];
  onMessagesChange: (messages: ChatMessage[]) => void;
}

function makeId(prefix: string): string {
  return `${prefix}-${crypto.randomUUID()}`;
}

async function* streamChunksFromReader(reader: ReadableStreamDefaultReader<Uint8Array>): AsyncGenerator<string> {
  const decoder = new TextDecoder();
  let buffer = "";

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      if (buffer.trim()) {
        yield buffer;
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    const events = buffer.split("\n\n");
    buffer = events.pop() ?? "";

    for (const event of events) {
      if (event.trim()) {
        yield event;
      }
    }

    await new Promise<void>((resolve) => {
      window.requestAnimationFrame(() => resolve());
    });
  }
}

export function useChatStream({ messages, onMessagesChange }: UseChatStreamOptions): HookState {
  const [isStreaming, setIsStreaming] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const abort = useCallback(() => {
    abortRef.current?.abort();
    setIsStreaming(false);
  }, []);

  const clearMessages = useCallback(() => {
    onMessagesChange([]);
  }, [onMessagesChange]);

  const sendMessage = useCallback(async (message: string): Promise<void> => {
    const content = sanitizeForDisplay(message);
    if (!content) return;

    setError(null);

    const userMessage: ChatMessage = {
      id: makeId("user"),
      role: "user",
      content,
      timestamp: Date.now(),
    };

    const assistantId = makeId("assistant");
    const assistantMessage: ChatMessage = {
      id: assistantId,
      role: "assistant",
      content: "",
      timestamp: Date.now(),
    };

    const baseMessages = [...messages, userMessage, assistantMessage];
    onMessagesChange(baseMessages);

    const controller = new AbortController();
    abortRef.current = controller;
    setIsStreaming(true);

    // Mutable accumulator for streaming
    let liveContent = "";

    const applyStreamChunk = (chunk: string): void => {
      liveContent = mergeChatText(liveContent, chunk);
      onMessagesChange([
        ...messages,
        userMessage,
        { ...assistantMessage, content: liveContent },
      ]);
    };

    const applySyncChunk = (chunk: string): void => {
      liveContent = mergeChatText(liveContent, chunk);
      onMessagesChange([
        ...messages,
        userMessage,
        { ...assistantMessage, content: liveContent },
      ]);
    };

    try {
      // Backend exposes /chat (sync). We simulate streaming with a typewriter effect.
      const syncResponse = await postChat(content);
      const tokens = syncResponse.response_text
        .split(/(\s+)/)
        .filter((t) => t.length > 0);

      for (const token of tokens) {
        if (controller.signal.aborted) break;
        applySyncChunk(token);
        await new Promise<void>((resolve) => {
          window.setTimeout(resolve, 18);
        });
      }
    } catch (chatError) {
      if (!controller.signal.aborted) {
        setError(mapApiError(chatError));
      }
    } finally {
      setIsStreaming(false);
      abortRef.current = null;
    }
  }, [messages, onMessagesChange]);

  return useMemo(
    () => ({
      messages,
      isStreaming,
      error,
      sendMessage,
      abort,
      clearMessages,
    }),
    [messages, isStreaming, error, sendMessage, abort, clearMessages]
  );
}
