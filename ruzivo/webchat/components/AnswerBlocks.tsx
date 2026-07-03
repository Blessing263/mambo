"use client";

import React from "react";
import type { Citation, Contact, Ministry } from "@/lib/types";

type ById = Record<string, Ministry>;

/* ---------- inline parsing → React nodes ---------- */
function renderInline(text: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const pattern = /\*\*(.+?)\*\*|\[(\d+)\]/g;
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(pattern)) {
    const idx = m.index ?? 0;
    if (idx > last) nodes.push(text.slice(last, idx));
    if (m[1] !== undefined) {
      nodes.push(<strong key={key++}>{m[1]}</strong>);
    } else if (m[2] !== undefined) {
      nodes.push(
        <sup key={key++} className="mx-0.5 rounded px-1 text-[10px] font-semibold"
          style={{ background: "var(--gold-light)", color: "var(--gold)" }}>
          {m[2]}
        </sup>,
      );
    }
    last = idx + m[0].length;
  }
  if (last < text.length) nodes.push(text.slice(last));
  return nodes;
}

export function AnswerText({ text }: { text: string }) {
  const blocks = text.trim().split(/\n\s*\n/);
  return (
    <div className="answer text-[15px]" style={{ color: "var(--text-primary)" }}>
      {blocks.map((block, bi) => {
        const lines = block.split("\n");
        const isList = lines.length > 0 && lines.every((l) => /^\s*[-*]\s+/.test(l));
        if (isList) {
          return (
            <ul key={bi}>
              {lines.map((l, li) => (
                <li key={li}>{renderInline(l.replace(/^\s*[-*]\s+/, ""))}</li>
              ))}
            </ul>
          );
        }
        return (
          <p key={bi}>
            {lines.map((l, li) => (
              <React.Fragment key={li}>
                {renderInline(l)}
                {li < lines.length - 1 ? <br /> : null}
              </React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

/* ---------- citation card ---------- */
export function CitationCard({ c, byId }: { c: Citation; byId: ById }) {
  const color = byId[c.ministry]?.accent_color || "#64748b";
  const isPdf = c.url?.toLowerCase().endsWith(".pdf");
  return (
    <a href={c.url} target="_blank" rel="noopener noreferrer"
      className="group flex items-start gap-2 rounded-lg border p-2.5 no-underline transition active:scale-[0.98]"
      style={{ borderColor: "var(--border-light)", background: "var(--bg-secondary)" }}>
      <span className="mt-0.5 h-6 w-1 shrink-0 rounded-full" style={{ backgroundColor: color }} aria-hidden />
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5 mb-0.5">
          <span className="block text-[13px] font-medium leading-snug break-words" style={{ color: "var(--text-primary)" }}>
            {c.title || "Official document"}
          </span>
          {isPdf && (
            <span className="shrink-0 rounded px-1.5 py-px text-[9px] font-semibold uppercase" style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}>PDF</span>
          )}
        </span>
        <span className="block text-[11px] break-words" style={{ color: "var(--text-tertiary)" }}>
          {byId[c.ministry]?.short_name ?? c.ministry}
          {c.page ? ` · p.${c.page}` : ""}
        </span>
      </span>
      <span className="material-symbols mt-0.5 shrink-0" style={{ fontSize: 15, color: "var(--text-tertiary)" }}>open_in_new</span>
    </a>
  );
}

/* ---------- ministry badge ---------- */
export function MinistryBadge({ id, byId }: { id: string; byId: ById }) {
  const m = byId[id];
  const color = m?.accent_color || "#64748b";
  return (
    <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium"
      style={{ borderColor: `${color}55`, backgroundColor: `${color}15`, color }}>
      {m?.short_name ?? id}
    </span>
  );
}

/* ---------- evidence status badge ---------- */
export function EvidenceBadge({ status }: { status?: string }) {
  if (!status) return null;
  const map: Record<string, { label: string; icon: string; color: string }> = {
    answered:    { label: "Answered from official sources", icon: "verified", color: "var(--accent)" },
    partial:     { label: "Partial evidence found", icon: "warning", color: "var(--gold)" },
    unsupported: { label: "No reliable official source — routed to the ministry", icon: "help", color: "var(--text-tertiary)" },
    declined:    { label: "Outside Ruzivo's scope", icon: "block", color: "var(--red)" },
  };
  const e = map[status] ?? map.unsupported;
  return (
    <span className="inline-flex items-center gap-1">
      <span className="material-symbols" style={{ fontSize: 14, color: e.color }}>{e.icon}</span>
      <span style={{ color: e.color }}>{e.label}</span>
    </span>
  );
}

/* ---------- contact card ---------- */
export function ContactCard({ c }: { c: Contact }) {
  const all: [string, string | null | undefined][] = [
    ["Phone", c.phone], ["WhatsApp", c.whatsapp], ["Email", c.email],
    ["Address", c.address], ["Hours", c.hours || c.office_hours],
  ];
  const fields = all.filter(([, v]) => v);
  if (!(fields.length || c.service_counter_url)) return null;
  return (
    <div className="rounded-lg border p-3" style={{ borderColor: "var(--border-light)", background: "var(--bg-secondary)" }}>
      <div className="mb-2 flex items-center gap-1.5 text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>
        <span className="material-symbols" style={{ fontSize: 16 }}>contact_phone</span>
        {c.ministry ? `${c.ministry} — how to reach them` : "How to reach them"}
        {c.last_verified_at && (
          <span className="ml-auto inline-flex items-center gap-0.5 rounded-full px-1.5 py-px text-[10px] font-medium"
            style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}
            title={`Contact last verified ${c.last_verified_at}`}>
            <span className="material-symbols" style={{ fontSize: 11 }}>verified</span>
            {c.last_verified_at}
          </span>
        )}
      </div>
      {fields.map(([k, v]) => (
        <div key={k} className="flex gap-2 text-[13px] leading-relaxed">
          <span className="w-20 shrink-0" style={{ color: "var(--text-tertiary)" }}>{k}</span>
          <span style={{ color: "var(--text-primary)" }}>{v}</span>
        </div>
      ))}
      {c.service_counter_url && (
        <a href={c.service_counter_url} target="_blank" rel="noopener noreferrer"
           className="mt-2 inline-flex items-center gap-1 text-[13px] no-underline"
           style={{ color: "var(--accent)" }}>
          <span className="material-symbols" style={{ fontSize: 15 }}>link</span>
          Service portal / counter
        </a>
      )}
    </div>
  );
}
