"use client";

import { useEffect, useMemo, useState } from "react";
import type { Ministry } from "@/lib/types";
import { MINISTRY_ICON, MINISTRY_SUBTITLE } from "@/lib/types";
import { ContactCard } from "./AnswerBlocks";

/* "Talk to a human" — the per-ministry human handover flow.
   Every ministry's verified contact (from the official registry, served by
   /api/ministries) is one tap away at any time — not only when an answer
   falls back. Pick a ministry, get the actionable contact card. */
export function HumanHandoff({
  open, onClose, ministries, selected,
}: {
  open: boolean;
  onClose: () => void;
  ministries: Ministry[];
  selected: string | null;
}) {
  const [picked, setPicked] = useState<string | null>(null);
  const byId = useMemo(
    () => Object.fromEntries(ministries.map((m) => [m.id, m])) as Record<string, Ministry>,
    [ministries],
  );

  // Opening pre-selects the ministry the chat is focused on (if any).
  useEffect(() => { if (open) setPicked(selected); }, [open, selected]);

  useEffect(() => {
    if (!open) return;
    const h = (e: KeyboardEvent) => { if (e.key === "Escape") onClose(); };
    window.addEventListener("keydown", h);
    return () => window.removeEventListener("keydown", h);
  }, [open, onClose]);

  if (!open) return null;
  const m = picked ? byId[picked] : null;
  const c = m ? { ...m.contact, ministry: m.short_name } : null;
  const hasContact = !!c && !!(c.phone || c.whatsapp || c.email || c.service_counter_url || c.address || c.hours || c.office_hours);

  return (
    <div className="fixed inset-0 z-50 grid place-items-center p-4" role="dialog" aria-modal="true" aria-label="Talk to a human">
      <div className="absolute inset-0 animate-fade-up" style={{ background: "rgba(10, 15, 12, 0.5)", animationDuration: "0.15s" }} onClick={onClose} aria-hidden="true" />
      <div className="relative w-full max-w-md rounded-2xl animate-scale-in"
        style={{ background: "var(--bg-primary)", border: "1px solid var(--border-light)", boxShadow: "var(--shadow-md)", maxHeight: "85dvh", overflowY: "auto" }}>
        <div className="flex items-center gap-2 px-4 py-3 sticky top-0" style={{ borderBottom: "1px solid var(--border-light)", background: "var(--bg-primary)" }}>
          {m && (
            <button onClick={() => setPicked(null)} className="grid h-8 w-8 place-items-center rounded-lg transition hover:bg-[var(--bg-hover)]"
              style={{ color: "var(--text-secondary)" }} aria-label="Back to ministry list">
              <span className="material-symbols" style={{ fontSize: 20 }}>arrow_back</span>
            </button>
          )}
          <span className="grid h-8 w-8 place-items-center rounded-lg" style={{ background: "var(--accent-light)" }}>
            <span className="material-symbols filled" style={{ fontSize: 18, color: "var(--accent)" }}>support_agent</span>
          </span>
          <span className="flex-1 min-w-0">
            <span className="block text-[15px] font-semibold font-display" style={{ color: "var(--text-primary)" }}>Talk to a human</span>
            <span className="block text-[11px]" style={{ color: "var(--text-tertiary)" }}>
              {m ? m.name : "Pick the ministry or agency you need"}
            </span>
          </span>
          <button onClick={onClose} className="grid h-8 w-8 place-items-center rounded-lg transition hover:bg-[var(--bg-hover)]"
            style={{ color: "var(--text-secondary)" }} aria-label="Close">
            <span className="material-symbols" style={{ fontSize: 20 }}>close</span>
          </button>
        </div>

        <div className="p-3">
          {m ? (
            <div className="space-y-2">
              {hasContact && c ? <ContactCard c={c} byId={byId} /> : (
                <p className="text-[13px] rounded-xl px-3 py-2.5 m-0" style={{ color: "var(--text-secondary)", background: "var(--bg-secondary)" }}>
                  No verified contact on record yet for {m.short_name} — try the ministry&apos;s official website.
                </p>
              )}
              <p className="text-[11px] px-1 m-0" style={{ color: "var(--text-tertiary)" }}>
                Contacts come from the official registry — never guessed — and are re-verified quarterly.
              </p>
            </div>
          ) : ministries.length === 0 ? (
            <p className="text-[13px] px-1 py-2 m-0" style={{ color: "var(--text-secondary)" }}>Loading ministries…</p>
          ) : (
            <div className="grid gap-1">
              {ministries.map((mm) => (
                <button key={mm.id} onClick={() => setPicked(mm.id)}
                  className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-left transition active:scale-[0.98] hover:bg-[var(--bg-hover)]">
                  <span className="grid h-9 w-9 shrink-0 place-items-center rounded-lg" style={{ background: `${mm.accent_color}1f` }}>
                    <span className="material-symbols" style={{ fontSize: 19, color: mm.accent_color }}>{MINISTRY_ICON[mm.id] ?? "account_balance"}</span>
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block text-[14px] font-medium leading-tight" style={{ color: "var(--text-primary)" }}>{mm.short_name}</span>
                    <span className="block text-[11px] leading-tight" style={{ color: "var(--text-tertiary)" }}>{MINISTRY_SUBTITLE[mm.id] ?? "Ministry"}</span>
                  </span>
                  <span className="material-symbols shrink-0" style={{ fontSize: 16, color: "var(--text-tertiary)" }}>chevron_right</span>
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
