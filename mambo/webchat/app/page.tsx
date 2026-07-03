"use client";

import { useEffect, useState, useCallback } from "react";
import { Chat } from "@/components/Chat";
import { Sidebar } from "@/components/Sidebar";
import { fetchMinistries } from "@/lib/api";
import type { Ministry } from "@/lib/types";

export default function Home() {
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [ministries, setMinistries] = useState<Ministry[]>([]);
  const [ministriesLoaded, setMinistriesLoaded] = useState(false);
  const [selected, setSelected] = useState<string | null>(null);
  const [chatStarted, setChatStarted] = useState(false);

  useEffect(() => {
    let cancelled = false;
    fetchMinistries()
      .then((m) => { if (!cancelled) { setMinistries(m); setMinistriesLoaded(true); } })
      .catch(() => { if (!cancelled) setMinistriesLoaded(true); });
    return () => { cancelled = true; };
  }, []);

  const toggleSidebar = useCallback(() => setSidebarOpen((v) => !v), []);

  return (
    <div style={{ display: "flex", minHeight: "100dvh" }}>
      <Sidebar
        open={sidebarOpen}
        ministries={ministries}
        ministriesLoaded={ministriesLoaded}
        selected={selected}
        onSelect={setSelected}
        onClose={() => setSidebarOpen(false)}
      />

      <main className="main-area flex w-full flex-col" style={{ transition: "margin-left 0.25s cubic-bezier(0.25,0.8,0.25,1)" }}>
        {/* Fixed top bar — only the hamburger (mobile) and new-chat button.
            On desktop the full logo + title live in the pinned sidebar. */}
        <div
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
            <span
              className="lg:hidden grid h-7 w-7 place-items-center rounded-lg text-sm font-bold text-white"
              style={{ background: "var(--accent)" }}
            >R</span>
            <span className="lg:hidden text-lg font-semibold tracking-tight" style={{ color: "var(--text-primary)" }}>
              Mambo<span style={{ color: "var(--gold)" }}>.</span>
            </span>

            {chatStarted && (
              <span className="ml-2 text-[12px] hidden sm:inline" style={{ color: "var(--text-tertiary)" }}>
                {selected ? ministries.find(m => m.id === selected)?.short_name ?? selected : "All of Government"}
              </span>
            )}
          </div>
          {chatStarted && (
            <button
              onClick={() => { setChatStarted(false); setSelected(null); }}
              className="grid h-9 w-9 place-items-center rounded-lg transition"
              style={{ color: "var(--text-secondary)" }}
              aria-label="New chat"
              title="New chat"
            >
              <span className="material-symbols font-ready" style={{ fontSize: 22 }}>add</span>
            </button>
          )}
        </div>

        {/* Full-height area below the fixed header — this scrolls internally.
            pt-[52px] compensates for the fixed bar height. */}
        <div className="flex flex-1 flex-col pt-[52px]" style={{ minHeight: "100dvh" }}>
          <Chat
            ministries={ministries}
            ministriesLoaded={ministriesLoaded}
            selected={selected}
            onSelect={setSelected}
            chatStarted={chatStarted}
            onChatStart={() => { setChatStarted(true); if (window.innerWidth < 1024) setSidebarOpen(false); }}
          />
        </div>
      </main>
    </div>
  );
}
