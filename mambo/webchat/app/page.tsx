"use client";

import { useEffect, useState, useCallback } from "react";
import { Chat } from "@/components/Chat";
import { Sidebar } from "@/components/Sidebar";
import { Mark, Wordmark } from "@/components/Brand";
import { HumanHandoff } from "@/components/HumanHandoff";
import { fetchMinistries } from "@/lib/api";
import type { Ministry } from "@/lib/types";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [ministries, setMinistries] = useState<Ministry[]>([]);
  const [ministriesLoaded, setMinistriesLoaded] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [chatStarted, setChatStarted] = useState(false);
  const [handoffOpen, setHandoffOpen] = useState(false);
  // Remount key for <Chat>: bumping it discards the conversation state.
  const [chatKey, setChatKey] = useState(0);

  useEffect(() => {
    let cancelled = false;
    fetchMinistries()
      .then((m) => { if (!cancelled) { setMinistries(m); setMinistriesLoaded(true); } })
      .catch(() => { if (!cancelled) setMinistriesLoaded(true); });
    return () => { cancelled = true; };
  }, []);

  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), []);

  // Changing the ministry focus mid-conversation starts a fresh chat, so answers
  // scoped to one ministry never bleed into another's context.
  const handleSelect = useCallback((id: string | null) => {
    setSelected(id);
    if (chatStarted) {
      setChatStarted(false);
      setChatKey((k) => k + 1);
    }
  }, [chatStarted]);

  const newChat = useCallback(() => {
    setChatStarted(false);
    setSelected(null);
    setChatKey((k) => k + 1);
  }, []);

  return (
    <div style={{ display: "flex", minHeight: "100dvh" }}>
      <Sidebar
        open={sidebarOpen}
        ministries={ministries}
        ministriesLoaded={ministriesLoaded}
        selected={selected}
        onSelect={handleSelect}
        onClose={() => setSidebarOpen(false)}
      />

      <HumanHandoff open={handoffOpen} onClose={() => setHandoffOpen(false)} ministries={ministries} selected={selected} />

      <main className="main-area flex w-full flex-col" style={{ transition: "margin-left 0.25s cubic-bezier(0.25,0.8,0.25,1)" }}>
        {/* Fixed top bar — only the hamburger (mobile) and new-chat button.
            On desktop the full logo + title live in the pinned sidebar. */}
        <header
          className="top-bar fixed top-0 right-0 z-30 flex shrink-0 items-center justify-between border-b px-3 py-2.5 sm:px-4"
          style={{ borderColor: "var(--border-primary)", background: "var(--bg-primary)", left: 0 }}
        >
          <div className="flex items-center gap-2">
            <button
              onClick={toggleSidebar}
              className="grid h-9 w-9 place-items-center rounded-lg transition lg:hidden"
              style={{ color: "var(--text-secondary)" }}
              aria-label="Toggle sidebar"
            >
              <span className="material-symbols" style={{ fontSize: 24 }}>menu</span>
            </button>

            {/* Mobile-only: logo + title (desktop has them in the pinned sidebar) */}
            <span className="lg:hidden flex items-center gap-2">
              <Mark size={26} />
              <Wordmark size={18} />
            </span>

            {chatStarted && (
              <span className="ml-2 text-[12px] hidden sm:inline" style={{ color: "var(--text-tertiary)" }}>
                {selected ? ministries.find(m => m.id === selected)?.short_name ?? selected : "All of Government"}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={() => setHandoffOpen(true)}
              className="flex h-9 items-center gap-1.5 rounded-lg px-2.5 transition hover:bg-[var(--bg-hover)]"
              style={{ color: "var(--text-secondary)", border: "1px solid var(--border-primary)", background: "var(--bg-surface)" }}
              aria-label="Talk to a human"
              title="Talk to a human at the ministry"
            >
              <span className="material-symbols" style={{ fontSize: 18 }}>support_agent</span>
              <span className="hidden sm:inline text-[12.5px] font-medium">Talk to a human</span>
            </button>
            {chatStarted && (
              <button
                onClick={newChat}
                className="grid h-9 w-9 place-items-center rounded-lg transition"
                style={{ color: "var(--text-secondary)" }}
                aria-label="New chat"
                title="New chat"
              >
                <span className="material-symbols font-ready" style={{ fontSize: 22 }}>add</span>
              </button>
            )}
          </div>
        </header>

        {/* Full-height area below the fixed header — this scrolls internally.
            pt-[52px] compensates for the fixed bar height. */}
        <div className="flex flex-1 flex-col pt-[52px]" style={{ minHeight: "100dvh" }}>
          <Chat
            key={chatKey}
            ministries={ministries}
            ministriesLoaded={ministriesLoaded}
            selected={selected}
            onSelect={handleSelect}
            chatStarted={chatStarted}
            onChatStart={() => { setChatStarted(true); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          />
        </div>
      </main>
    </div>
  );
}
