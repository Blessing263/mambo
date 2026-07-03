"use client";

import type { Ministry } from "@/lib/types";
import { MINISTRY_ICON, MINISTRY_SUBTITLE } from "@/lib/types";
import { ThemeToggle } from "./ThemeToggle";

// Static fallback so the sidebar never shows an empty list during the brief
// window before the /api/ministries call resolves. These are the same 8
// ministries the API returns (id + short_name only) — once the API resolves,
// the real objects (with mandate, contact, accent_color) replace them.
const FALLBACK_MINISTRIES: Pick<Ministry, "id" | "short_name" | "accent_color">[] = [
  { id: "ict",         short_name: "ICT",          accent_color: "#1F8A4C" },
  { id: "health",      short_name: "Health",       accent_color: "#C0392B" },
  { id: "home_affairs",short_name: "Home Affairs", accent_color: "#2C3E70" },
  { id: "finance",     short_name: "Finance",      accent_color: "#B8860B" },
  { id: "education",   short_name: "Education",    accent_color: "#2E86C1" },
  { id: "zimra",       short_name: "ZIMRA",        accent_color: "#D4A017" },
  { id: "zimsec",      short_name: "ZIMSEC",       accent_color: "#6C3483" },
  { id: "veritas",     short_name: "Veritas (Law)",accent_color: "#8B4513" },
];

export function Sidebar({
  open,
  ministries,
  ministriesLoaded,
  selected,
  onSelect,
  onClose,
}: {
  open: boolean;
  ministries: Ministry[];
  ministriesLoaded: boolean;
  selected: string | null;
  onSelect: (id: string | null) => void;
  onClose: () => void;
}) {
  // Use the live API data if we have it, otherwise the static fallback so the
  // sidebar is never visually empty.
  const list = ministries.length > 0
    ? ministries
    : FALLBACK_MINISTRIES;

  return (
    <>
      <div
        className={`sidebar-overlay${open ? " open" : ""}`}
        onClick={onClose}
        aria-hidden="true"
      />
      <aside
        className={`sidebar${open ? " open" : ""}`}
        aria-label="Ministry sources"
      >
        <div className="flex h-full flex-col">
          {/* Header */}
          <div
            className="flex items-center justify-between border-b px-4 py-3.5"
            style={{ borderColor: "var(--border-primary)" }}
          >
            <div className="flex items-center gap-2.5">
              <span
                className="grid h-7 w-7 place-items-center rounded-lg text-sm font-bold text-white"
                style={{ background: "var(--accent)" }}
              >
                R
              </span>
              <span
                className="text-[17px] font-semibold tracking-tight"
                style={{ color: "var(--text-primary)" }}
              >
                Ruzivo<span style={{ color: "var(--gold)" }}>.</span>
              </span>
            </div>
            <button
              onClick={onClose}
              className="grid h-8 w-8 place-items-center rounded-lg transition lg:hidden"
              style={{ color: "var(--text-secondary)" }}
              aria-label="Close sidebar"
            >
              <span className="material-symbols" style={{ fontSize: 22 }}>close</span>
            </button>
          </div>

          {/* Ministry list */}
          <div
            className="flex-1 overflow-y-auto scroll-thin px-2 py-3"
            aria-busy={!ministriesLoaded}
          >
            <p
              className="mb-2 px-3 text-[11px] font-semibold uppercase tracking-wider"
              style={{ color: "var(--text-tertiary)" }}
            >
              Sources
            </p>
            <SidebarItem
              active={selected === null}
              onClick={() => { onSelect(null); onClose(); }}
              icon="public"
              label="All of Government"
              color="#1f8a4c"
            />
            {list.map((m) => (
              <SidebarItem
                key={m.id}
                active={selected === m.id}
                onClick={() => { onSelect(m.id); onClose(); }}
                icon={MINISTRY_ICON[m.id] ?? "account_balance"}
                label={m.short_name}
                color={m.accent_color}
                subtitle={MINISTRY_SUBTITLE[m.id]}
              />
            ))}
            {!ministriesLoaded && ministries.length === 0 && (
              <div className="px-3 py-2" aria-hidden="true">
                <span className="skeleton" style={{ height: 16, width: "70%", marginBottom: 8 }} />
                <span className="skeleton" style={{ height: 16, width: "55%", marginBottom: 8 }} />
                <span className="skeleton" style={{ height: 16, width: "65%" }} />
              </div>
            )}
          </div>

          {/* Footer */}
          <div
            className="border-t px-4 py-3"
            style={{ borderColor: "var(--border-primary)" }}
          >
            <ThemeToggle />
            <div
              className="mt-3 flex items-center gap-2 rounded-lg px-2 py-2"
              style={{ background: "var(--bg-hover)" }}
            >
              <span
                className="material-symbols"
                style={{ fontSize: 16, color: "var(--gold)" }}
              >
                verified
              </span>
              <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                Answers from official documents only
              </span>
            </div>
          </div>
        </div>
      </aside>
    </>
  );
}

function SidebarItem({
  active, onClick, icon, label, color, subtitle,
}: {
  active: boolean; onClick: () => void; icon: string; label: string; color: string; subtitle?: string;
}) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition active:scale-[0.98]"
      style={{
        background: active ? `${color}15` : "transparent",
        color: active ? "var(--text-primary)" : "var(--text-secondary)",
      }}
    >
      <span
        className="material-symbols shrink-0"
        style={{ fontSize: 20, color: active ? color : "var(--text-tertiary)" }}
      >
        {icon}
      </span>
      <span className="min-w-0">
        <span className="block text-[14px] font-medium leading-tight">{label}</span>
        {subtitle && (
          <span
            className="block text-[11px] leading-tight"
            style={{ color: "var(--text-tertiary)" }}
          >
            {subtitle}
          </span>
        )}
      </span>
    </button>
  );
}
