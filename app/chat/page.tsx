"use client";

import Link from "next/link";
import Image from "next/image";

import { PanelLeftClose, PanelLeftOpen, LayoutDashboard, ChevronLeft } from "lucide-react";
import { motion } from "framer-motion";
import { useState } from "react";

import { ChatWindow } from "@/components/ChatWindow";
import { SettingsPanel } from "@/components/SettingsPanel";
import { ChatHistorySidebar } from "@/components/ChatHistorySidebar";
import { useChatStream } from "@/hooks/useChatStream";
import { useChatHistory } from "@/hooks/useChatHistory";
import { useSettings } from "@/hooks/useSettings";

export default function ChatPage(): JSX.Element {
  const {
    sessions,
    activeSessionId,
    activeMessages,
    createSession,
    switchSession,
    deleteSession,
    deleteAllSessions,
    updateActiveMessages,
  } = useChatHistory();

  const { messages, isStreaming, error, sendMessage } = useChatStream({
    messages: activeMessages,
    onMessagesChange: (msgs) => {
      // Auto-create a session if there is none
      if (!activeSessionId) {
        createSession();
      }
      updateActiveMessages(msgs);
    },
  });

  const { settings, updateSettings, resetSettings } = useSettings();
  const [settingsOpen, setSettingsOpen] = useState<boolean>(false);
  const [historyOpen, setHistoryOpen] = useState<boolean>(true);


  const handleNewChat = () => {
    createSession();
  };

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: "easeOut" }}
      className="mx-auto flex max-w-[1400px] gap-4 h-[calc(100vh-3rem)]"
    >
      {/* Chat History Sidebar */}
      <motion.aside
        animate={{ width: historyOpen ? 260 : 0, opacity: historyOpen ? 1 : 0 }}
        transition={{ duration: 0.3, ease: "easeInOut" }}
        className="glass shadow-glass shrink-0 overflow-hidden rounded-3xl transition-all duration-500 hover:shadow-glass-hover"
      >
        <ChatHistorySidebar
          sessions={sessions}
          activeSessionId={activeSessionId}
          onNewChat={handleNewChat}
          onSwitch={switchSession}
          onDelete={deleteSession}
          onDeleteAll={deleteAllSessions}
        />
      </motion.aside>

      {/* Main Chat Area */}
      <section className="flex flex-1 flex-col gap-4 min-w-0">
        {/* Top Nav Bar */}
        <header className="glass shadow-glass flex shrink-0 items-center justify-between rounded-2xl px-6 py-3 transition-all duration-500 hover:-translate-y-1 hover:shadow-glass-hover">
          <div className="flex items-center gap-3">
            {/* History toggle */}
            <button
              type="button"
              onClick={() => setHistoryOpen((o) => !o)}
              title="Toggle chat history"
              className="rounded-xl border border-panel-border bg-panel-glass p-2 text-text shadow-sm transition-colors hover:bg-accent/10 hover:text-accent"
              aria-label="Toggle history sidebar"
            >
              {historyOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeftOpen className="h-5 w-5" />}
            </button>
            <Link href="/" className="flex items-center gap-2 rounded-full transition-transform hover:scale-105" aria-label="Go home">
              <Image src="/logo.png" alt="DeBias" width={32} height={32} className="drop-shadow-sm" />
              <span className="hidden font-bold text-text sm:inline">DeBias</span>
            </Link>
            <div>
              <h2 className="text-xl font-bold tracking-tight text-text">Live Chat</h2>
              <p className="text-xs text-muted">Streaming responses with real-time bias detection.</p>
            </div>
          </div>
          <div className="flex items-center gap-3">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 rounded-xl bg-gradient-to-r from-purple-500 to-accent px-4 py-2 text-sm font-semibold text-white shadow-floating transition-transform hover:scale-105"
            >
              <LayoutDashboard size={16} />
              <span className="hidden sm:inline">Dashboard</span>
            </Link>
            <button
              type="button"
              onClick={() => setSettingsOpen((open) => !open)}
              className="rounded-xl border border-panel-border bg-panel-glass p-2 text-text shadow-sm backdrop-blur-md transition-colors hover:bg-muted/10 lg:hidden"
              aria-expanded={settingsOpen}
              aria-controls="settings-drawer"
              aria-label="Toggle settings panel"
            >
              {settingsOpen ? <PanelLeftClose className="h-5 w-5" /> : <PanelLeftOpen className="h-5 w-5" />}
            </button>
          </div>
        </header>

        {/* Chat + Settings row */}
        <div className="flex flex-1 gap-4 overflow-hidden">
          <div className="glass shadow-glass flex-1 overflow-hidden rounded-3xl transition-all duration-500 hover:shadow-glass-hover">
            <ChatWindow
              onSend={(msg) => void sendMessage(msg)}
              messages={messages}
              isStreaming={isStreaming}
              error={error}
            />
          </div>

          <div
            id="settings-drawer"
            className={`transition-all duration-300 ${settingsOpen ? "block" : "hidden lg:block"} w-72 shrink-0`}
          >
            <div className="glass shadow-glass sticky top-6 rounded-3xl p-5 transition-all duration-500 hover:-translate-y-1 hover:shadow-glass-hover">
              <SettingsPanel settings={settings} onChange={updateSettings} onReset={resetSettings} />
            </div>
          </div>
        </div>
      </section>
    </motion.div>
  );
}
