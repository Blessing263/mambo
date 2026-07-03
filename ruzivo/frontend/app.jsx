/* ============================================================
   App shell — live RAG API, top bar, theme, sidebar, mount.
   Same visual identity, now wired to /api/ask/stream.
   ============================================================ */
const { useState: useStateApp, useEffect: useEffectApp, useRef: useRefApp, useCallback } = React;

function App() {
  const [theme, setTheme] = useStateApp("dark");
  const [sidebarOpen, setSidebarOpen] = useStateApp(false);
  const [selected, setSelected] = useStateApp(null);
  const [started, setStarted] = useStateApp(false);
  const [messages, setMessages] = useStateApp([]);
  const [busy, setBusy] = useStateApp(false);
  const [routerOpen, setRouterOpen] = useStateApp(false);
  const composerRef = useRefApp(null);

  const handleSelect = useCallback((id) => {
    if (id !== selected) {
      setMessages([]);
      setStarted(false);
    }
    setSelected(id);
  }, [selected]);

  useEffectApp(() => {
    const saved = localStorage.getItem("ruzivo-theme");
    if (saved) setTheme(saved);
  }, []);
  useEffectApp(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ruzivo-theme", theme);
  }, [theme]);

  const patch = useCallback((id, fn) => {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
  }, []);

  const send = useCallback((question) => {
    if (busy || !question.trim()) return;
    if (!started) setStarted(true);
    setBusy(true);

    // Build conversation history from prior (non-streaming) messages
    const history = messages
      .filter((m) => !m.streaming && m.text)
      .slice(-6)
      .map((m) => ({ role: m.role, content: m.text }));

    const aId = window.nextId();
    const userMsg = { id: window.nextId(), role: "user", text: question };
    const asstMsg = { id: aId, role: "assistant", text: "", streaming: true };
    setMessages((prev) => [...prev, userMsg, asstMsg]);

    window.RUZIVO.askLive(question, history, selected, {
      onDelta(text) {
        patch(aId, (m) => ({ ...m, text: m.text + text }));
      },
      onStatus(text) {
        patch(aId, (m) => ({ ...m, status: text }));
      },
      onDone(meta) {
        patch(aId, (m) => ({
          ...m, streaming: false, status: undefined,
          meta: {
            source_ministry: meta.source_ministry,
            citations: meta.citations,
            confident: meta.confident,
            fallback_contact: meta.fallback_contact,
          },
        }));
        setBusy(false);
      },
      onError() {
        patch(aId, (m) => ({ ...m, streaming: false,
          text: m.text || "Sorry — I couldn't reach the service just now. Please try again in a moment.",
        }));
        setBusy(false);
      },
    });
  }, [busy, started, selected, messages]);

  const newChat = useCallback(() => {
    setStarted(false); setMessages([]); setSelected(null); setBusy(false);
  }, []);

  const focusName = selected ? window.RUZIVO.byId[selected]?.short : "All of Government";

  return (
    <div style={{ height: "100%", display: "flex" }}>
      <Sidebar
        open={sidebarOpen}
        selected={selected}
        onSelect={handleSelect}
        onClose={() => setSidebarOpen(false)}
        theme={theme}
        onToggleTheme={() => setTheme((t) => (t === "dark" ? "light" : "dark"))}
        onNewChat={newChat}
      />

      <main className="main">
        <div className="halo" />
        <header className="topbar">
          <div className="tb-left">
            <button className="tb-icon only-mobile" onClick={() => setSidebarOpen(true)} aria-label="Menu">
              <Ico n="menu" style={{ fontSize: 24 }} />
            </button>
            <div className="only-mobile" style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <Mark size={26} radius={8} />
              <Wordmark size={18} />
            </div>
            {started && (
              <div className="tb-focus">
                <Ico n={selected ? window.RUZIVO.byId[selected]?.icon : "public"} style={{ fontSize: 15, color: "var(--accent)" }} />
                {focusName}
              </div>
            )}
          </div>
          <div className="tb-right">
            <button className="tb-icon" onClick={() => setTheme((t) => (t === "dark" ? "light" : "dark"))} aria-label="Toggle theme" title="Toggle theme">
              <Ico n={theme === "dark" ? "light_mode" : "dark_mode"} style={{ fontSize: 20 }} />
            </button>
            {started && (
              <button className="tb-icon" onClick={newChat} aria-label="New question" title="New question">
                <Ico n="add" style={{ fontSize: 22 }} />
              </button>
            )}
          </div>
        </header>

        <div className="main-body">
          <Chat
            started={started}
            selected={selected}
            onSelect={handleSelect}
            messages={messages}
            busy={busy}
            onSend={send}
            composerRef={composerRef}
          />
        </div>
      </main>

      <style>{`
        .main { position: relative; flex: 1; display: flex; flex-direction: column; min-width: 0; height: 100%; }
        @media (min-width: 1040px) { .main { margin-left: 276px; } }
        .halo { position: absolute; inset: 0; background: var(--halo); pointer-events: none; z-index: 0; }
        .topbar {
          position: relative; z-index: 5; display: flex; align-items: center; justify-content: space-between;
          padding: 10px 16px; border-bottom: 1px solid var(--line); background: color-mix(in srgb, var(--bg) 82%, transparent);
          backdrop-filter: blur(10px); min-height: 56px;
        }
        .tb-left, .tb-right { display: flex; align-items: center; gap: 8px; }
        .tb-icon {
          width: 40px; height: 40px; border-radius: 11px; border: none; background: transparent; cursor: pointer;
          color: var(--ink-soft); display: grid; place-items: center; transition: all .15s;
        }
        .tb-icon:hover { background: var(--surface); color: var(--ink); }
        .tb-focus {
          display: inline-flex; align-items: center; gap: 7px; padding: 6px 13px; border-radius: var(--r-pill);
          border: 1px solid var(--line); background: var(--surface); font-size: 12.5px; font-weight: 600; color: var(--ink-soft);
          margin-left: 4px;
        }
        .main-body { position: relative; z-index: 1; flex: 1; display: flex; flex-direction: column; min-height: 0; }
        .thread { max-width: 720px; margin: 0 auto; width: 100%; padding: 26px 20px 40px; }
        .user-row { display: flex; justify-content: flex-end; margin-bottom: 26px; }
        .user-bubble {
          max-width: 80%; padding: 11px 16px; border-radius: 18px 18px 5px 18px; font-size: 15px; line-height: 1.5;
          background: var(--user-bubble); border: 1px solid var(--user-line); color: var(--ink);
        }
        .only-mobile { display: none; }
        @media (max-width: 1039px) { .only-mobile { display: flex; } }
      `}</style>
    </div>
  );
}

/* Simple per-component id counter — used by chat + app */
let _mid2 = 0;
window.nextId = () => `m${++_mid2}`;

ReactDOM.createRoot(document.getElementById("root")).render(<App />);
