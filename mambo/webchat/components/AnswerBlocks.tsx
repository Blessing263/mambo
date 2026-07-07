"use client";

import React, { useState } from "react";
import type { Citation, Contact, Ministry, ServiceJourney } from "@/lib/types";
import { MINISTRY_ICON } from "@/lib/types";

type ById = Record<string, Ministry>;

/* ---------- inline parsing → React nodes (reused everywhere) ---------- */
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
        <sup key={key++} className="mx-0.5 rounded px-1 text-[10px] font-semibold align-super"
          style={{ background: "var(--gold-light)", color: "var(--gold)" }}>{m[2]}</sup>,
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
    <div className="answer" style={{ color: "var(--text-primary)" }}>
      {blocks.map((block, bi) => {
        const lines = block.split("\n");
        const isList = lines.length > 0 && lines.every((l) => /^\s*[-*]\s+/.test(l));
        if (isList) {
          return (
            <ul key={bi}>{lines.map((l, li) => <li key={li}>{renderInline(l.replace(/^\s*[-*]\s+/, ""))}</li>)}</ul>
          );
        }
        return (
          <p key={bi}>
            {lines.map((l, li) => (
              <React.Fragment key={li}>{renderInline(l)}{li < lines.length - 1 ? <br /> : null}</React.Fragment>
            ))}
          </p>
        );
      })}
    </div>
  );
}

/* ---------- shared actions: copy / share / print / feedback ---------- */
export function AnswerActions({ text, sessionId, question }: { text: string; sessionId?: string | null; question?: string }) {
  const [fb, setFb] = useState<1 | -1 | null>(null);
  const [copied, setCopied] = useState(false);
  const copy = () => navigator.clipboard?.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1600); }).catch(() => {});
  const share = () => { if (navigator.share) navigator.share({ title: "Mambo answer", text }).catch(() => {}); else copy(); };
  const rate = (v: 1 | -1) => {
    const next = fb === v ? null : v;
    setFb(next);
    if (next && question) {
      import("@/lib/api").then((m) => m.submitFeedback(sessionId ?? null, question, next)).catch(() => {});
    }
  };
  const Btn = ({ label, icon, onClick, on }: { label: string; icon: string; onClick: () => void; on?: boolean }) => (
    <button aria-label={label} onClick={onClick} className="rounded-md p-1.5 transition hover:bg-[var(--bg-hover)]"
      style={{ color: on ? (icon === "thumb_up" ? "var(--accent)" : "var(--red)") : "var(--text-tertiary)" }}>
      <span className="material-symbols" style={{ fontSize: 16 }}>{icon}</span>
    </button>
  );
  return (
    <div className="flex items-center" style={{ color: "var(--text-tertiary)" }}>
      <Btn label="Copy answer" icon={copied ? "check" : "content_copy"} onClick={copy} on={copied} />
      <Btn label="Share answer" icon="share" onClick={share} />
      <Btn label="Print" icon="print" onClick={() => window.print()} />
      <Btn label="Helpful" icon="thumb_up" onClick={() => rate(1)} on={fb === 1} />
      <Btn label="Not helpful" icon="thumb_down" onClick={() => rate(-1)} on={fb === -1} />
    </div>
  );
}

/* ---------- citation card (snippet + doc-type + numbered) ---------- */
export function CitationCard({ c, index, byId }: { c: Citation; index: number; byId: ById }) {
  const color = byId[c.ministry]?.accent_color || "#64748b";
  const n = index + 1;
  const pdf = c.doc_type === "pdf" || (!c.doc_type && c.url?.toLowerCase().endsWith(".pdf"));
  return (
    <a href={c.url} target="_blank" rel="noopener noreferrer" aria-label={`Open source: ${c.title || "official document"}`}
      className="group flex items-start gap-2.5 rounded-xl border p-3 no-underline transition active:scale-[0.99] animate-scale-in"
      style={{ borderColor: "var(--border-light)", background: "var(--bg-secondary)", animationDelay: `${index * 70}ms` }}>
      <span className="mt-0.5 self-stretch w-1 shrink-0 rounded-full" style={{ background: `linear-gradient(180deg, ${color}, ${color}aa)` }} aria-hidden />
      <span className="grid h-5 w-5 shrink-0 place-items-center rounded-md text-[11px] font-bold" style={{ background: `${color}22`, color }}>{n}</span>
      <span className="min-w-0 flex-1">
        <span className="flex items-center gap-1.5">
          <span className="material-symbols" style={{ fontSize: 14, color }}>{pdf ? "picture_as_pdf" : "description"}</span>
          <span className="block text-[13px] font-semibold leading-snug break-words" style={{ color: "var(--text-primary)" }}>{c.title || "Official document"}</span>
          {pdf && <span className="shrink-0 rounded px-1 py-px text-[9px] font-bold uppercase" style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}>PDF</span>}
        </span>
        <span className="block text-[11px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
          {byId[c.ministry]?.short_name ?? c.ministry}{c.page ? ` · p.${c.page}` : ""}
        </span>
        {c.snippet && (
          <span className="block text-[12px] mt-1 leading-snug" style={{
            color: "var(--text-secondary)", display: "-webkit-box", WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical", overflow: "hidden",
          }}>{c.snippet}</span>
        )}
      </span>
      <span className="material-symbols mt-0.5 shrink-0 transition group-hover:text-[var(--accent)]" style={{ fontSize: 15, color: "var(--text-tertiary)" }}>open_in_new</span>
    </a>
  );
}

/* ---------- ministry badge ---------- */
export function MinistryBadge({ id, byId }: { id: string; byId: ById }) {
  const m = byId[id];
  const color = m?.accent_color || "#64748b";
  return (
    <span className="inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px] font-medium"
      style={{ borderColor: `${color}55`, backgroundColor: `${color}15`, color: "var(--text-secondary)" }}>
      <span className="inline-block h-1.5 w-1.5 rounded-full" style={{ background: color }} />
      {m?.short_name ?? id}
    </span>
  );
}

/* ---------- evidence status: prominent header ---------- */
export function EvidenceHeader({ status }: { status?: string }) {
  if (!status) return null;
  const map: Record<string, { label: string; icon: string; color: string; bg: string; expl: string }> = {
    answered: { label: "Answered from official sources", icon: "verified", color: "var(--accent)", bg: "var(--accent-light)", expl: "Every claim is grounded in the official documents cited below." },
    partial: { label: "Partial evidence found", icon: "warning", color: "var(--gold)", bg: "var(--gold-light)", expl: "Parts of this answer are grounded; others are uncertain — see the sources." },
    unsupported: { label: "No reliable official source", icon: "help", color: "var(--text-secondary)", bg: "var(--bg-hover)", expl: "The official documents don't cover this — here's who to contact." },
    declined: { label: "Outside Mambo's scope", icon: "block", color: "var(--red)", bg: "var(--red-light)", expl: "I can't help with this, but I'll point you to the right place." },
  };
  const e = map[status] ?? map.unsupported;
  return (
    <div className="flex items-start gap-2 rounded-xl px-3 py-2 animate-rise" style={{ background: e.bg, borderLeft: `3px solid ${e.color}` }}>
      <span className="material-symbols filled" style={{ fontSize: 18, color: e.color }}>{e.icon}</span>
      <span className="flex flex-col">
        <span className="text-[13px] font-semibold font-display" style={{ color: e.color }}>{e.label}</span>
        <span className="text-[11px]" style={{ color: "var(--text-secondary)" }}>{e.expl}</span>
      </span>
    </div>
  );
}

/* ---------- declined referral card ---------- */
const REFERRALS: Record<string, { title: string; icon: string; body: string }> = {
  medical_advice: { title: "Speak to a clinician", icon: "local_hospital", body: "I can't diagnose or recommend treatment. Please contact your nearest clinic or hospital, or a qualified health professional." },
  legal_advice: { title: "Consult a legal practitioner", icon: "gavel", body: "I can't give legal advice or tell you whether to act. The Law Society of Zimbabwe can refer you to a registered lawyer; meanwhile here are the public legal sources." },
  personal_data: { title: "Contact the office directly", icon: "badge", body: "I can't look up or share people's personal details. For official records about yourself, contact the relevant ministry or office directly." },
  political: { title: "I stay neutral", icon: "how_to_vote", body: "I don't express political opinions or endorse parties or candidates. I stick to official, factual government information." },
  prompt_injection: { title: "I can't do that", icon: "block", body: "I can only help with official Zimbabwe government information. I can't ignore my instructions or reveal how I work." },
};
export function ReferralCard({ reason }: { reason?: string | null }) {
  const r = reason ? REFERRALS[reason] : null;
  if (!r) return null;
  return (
    <div className="rounded-xl p-3.5 animate-rise" style={{ background: "var(--red-light)", border: "1px solid var(--border-light)" }}>
      <div className="flex items-center gap-2 mb-1.5">
        <span className="grid h-8 w-8 place-items-center rounded-lg" style={{ background: "var(--red)", color: "#fff" }}>
          <span className="material-symbols filled" style={{ fontSize: 18 }}>{r.icon}</span>
        </span>
        <span className="text-[15px] font-semibold font-display" style={{ color: "var(--text-primary)" }}>{r.title}</span>
      </div>
      <p className="text-[13px] m-0" style={{ color: "var(--text-secondary)" }}>{r.body}</p>
    </div>
  );
}

/* ---------- actionable handoff card ---------- */
const waLink = (n?: string | null) => (n ? `https://wa.me/${n.replace(/[^\d]/g, "")}` : null);
const telLink = (n?: string | null) => (n ? `tel:${n.replace(/[^\d+]/g, "")}` : null);

export function ContactCard({ c, byId }: { c: Contact; byId?: ById }) {
  const m = byId ? Object.values(byId).find((x) => x.short_name === c.ministry) : undefined;
  const color = m?.accent_color || "#64748b";
  const tel = telLink(c.phone), wa = waLink(c.whatsapp || c.phone);
  const rows: [string, string | null | undefined][] = [["location_on", c.address], ["schedule", c.hours || c.office_hours]].filter(([, v]) => v) as [string, string][];
  if (!(tel || wa || c.email || c.service_counter_url || rows.length)) return null;
  const Action = ({ href, icon, label, primary, target }: { href: string; icon: string; label: string; primary?: boolean; target?: string }) => (
    <a href={href} target={target} rel="noopener noreferrer"
      className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg no-underline transition active:scale-[0.98]"
      style={primary ? { background: "var(--accent)", color: "#fff", fontWeight: 600, fontSize: 13 } : { border: "1px solid var(--border-primary)", color: "var(--text-secondary)", fontWeight: 600, fontSize: 13 }}>
      <span className="material-symbols" style={{ fontSize: 15 }}>{icon}</span>{label}
    </a>
  );
  return (
    <div className="rounded-xl p-3.5 animate-scale-in" style={{ background: "var(--grad-surface)", border: "1px solid var(--border-light)", boxShadow: "var(--shadow-sm)" }}>
      <div className="flex items-center gap-2.5 mb-3 pb-2.5" style={{ borderBottom: "1px solid var(--border-light)" }}>
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg" style={{ background: `linear-gradient(135deg, ${color}, ${color}cc)` }}>
          <span className="material-symbols filled" style={{ fontSize: 17, color: "#fff" }}>{(m?.id && MINISTRY_ICON[m.id]) || "account_balance"}</span>
        </span>
        <span className="flex-1 min-w-0">
          <span className="block text-[14px] font-semibold font-display" style={{ color: "var(--text-primary)" }}>How to reach {c.ministry || "the ministry"}</span>
          {c.last_verified_at && (
            <span className="inline-flex items-center gap-0.5 text-[10px] mt-0.5" style={{ color: "var(--text-tertiary)" }}>
              <span className="material-symbols" style={{ fontSize: 11 }}>verified</span>Verified {c.last_verified_at}
            </span>
          )}
        </span>
      </div>
      <div className="flex flex-wrap gap-2 mb-1">
        {tel && <Action href={tel} icon="call" label="Call" primary />}
        {wa && <Action href={wa} icon="chat" label="WhatsApp" target="_blank" primary />}
        {c.email && <Action href={`mailto:${c.email}`} icon="mail" label="Email" />}
        {c.service_counter_url && <Action href={c.service_counter_url} icon="language" label="Portal" target="_blank" />}
      </div>
      {rows.map(([ic, v]) => (
        <div key={ic} className="flex gap-2 text-[12.5px] py-0.5">
          <span className="material-symbols shrink-0" style={{ fontSize: 15, color: "var(--text-tertiary)" }}>{ic}</span>
          <span style={{ color: "var(--text-secondary)" }}>{v}</span>
        </div>
      ))}
    </div>
  );
}

/* ---------- service journey card ---------- */
const SECTION_ICON: Record<string, string> = {
  eligibility: "check_circle", "what to bring": "inventory_2", "what you need": "inventory_2",
  steps: "format_list_numbered", fees: "payments",
  "where to apply": "place", "where to register": "place", "expected timeline": "schedule",
};
const sectionIcon = (name: string) => SECTION_ICON[name.toLowerCase()] || "circle";

function parseSections(text: string, known: string[]): { name: string; body: string }[] {
  const knownLower = new Set(known.map((k) => k.toLowerCase()));
  const lines = text.split("\n");
  const out: { name: string; body: string }[] = [];
  let cur: { name: string; body: string } | null = null;
  const pre: string[] = [];
  for (const line of lines) {
    const m = line.match(/^\s*\*\*(.+?)\*\*:?\s*$/);
    if (m && knownLower.has(m[1].toLowerCase())) {
      if (cur) out.push(cur);
      cur = { name: m[1], body: "" };
    } else if (cur) {
      cur.body += (cur.body ? "\n" : "") + line;
    } else {
      pre.push(line);
    }
  }
  if (cur) out.push(cur);
  const intro = pre.join("\n").trim();
  if (intro) out.unshift({ name: "", body: intro });
  return out;
}

function JourneySection({ name, body }: { name: string; body: string }) {
  const trimmed = body.trim();
  if (!name) return trimmed ? <AnswerText text={trimmed} /> : null;
  const notSpecified = /not specified in the official documents/i.test(trimmed);
  return (
    <div className="flex gap-3">
      <span className="material-symbols shrink-0 mt-0.5" style={{ fontSize: 18, color: notSpecified ? "var(--text-tertiary)" : "var(--accent)" }}>{sectionIcon(name)}</span>
      <div className="flex-1 min-w-0">
        <div className="text-[11px] font-semibold uppercase tracking-wide mb-0.5" style={{ color: "var(--text-tertiary)" }}>{name}</div>
        {notSpecified ? (
          <span className="inline-block text-[13px] italic rounded-md px-2.5 py-1.5" style={{ color: "var(--text-tertiary)", border: "1px dashed var(--border-primary)" }}>Not specified in the official documents</span>
        ) : <AnswerText text={trimmed} />}
      </div>
    </div>
  );
}

export function JourneyCard({ text, journey, byId }: { text: string; journey: ServiceJourney; byId: ById }) {
  const color = byId[journey.ministry]?.accent_color || "#64748b";
  const sections = parseSections(text, journey.sections);
  return (
    <div className="printable rounded-2xl overflow-hidden animate-scale-in"
      style={{ background: "var(--grad-surface)", border: "1px solid var(--border-light)", boxShadow: "var(--shadow-md)", borderTop: `3px solid ${color}` }}>
      <div className="flex items-center gap-2.5 px-4 py-3" style={{ borderBottom: "1px solid var(--border-light)" }}>
        <span className="grid h-8 w-8 shrink-0 place-items-center rounded-lg" style={{ background: `${color}1f` }}>
          <span className="material-symbols" style={{ fontSize: 18, color }}>{journey.icon || (MINISTRY_ICON[journey.ministry] ?? "task_alt")}</span>
        </span>
        <span className="flex-1 min-w-0">
          <span className="block text-[15px] font-semibold font-display" style={{ color: "var(--text-primary)" }}>{journey.title}</span>
        </span>
        <MinistryBadge id={journey.ministry} byId={byId} />
      </div>
      <div className="px-4 py-3.5 space-y-3.5">{sections.map((s, i) => <JourneySection key={i} name={s.name} body={s.body} />)}</div>
      <div className="flex items-center justify-end px-3 py-2" style={{ borderTop: "1px solid var(--border-light)" }}>
        <AnswerActions text={text} />
      </div>
    </div>
  );
}
