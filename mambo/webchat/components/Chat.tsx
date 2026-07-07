"use client";

import React, { useEffect, useRef, useState, useMemo } from "react";
import { askStream } from "@/lib/api";
import type { ChatMessage, Ministry, StatusEvent } from "@/lib/types";
import { JOURNEYS, getJourney } from "@/lib/journeys";
import {
  AnswerText, CitationCard, ContactCard, EvidenceHeader, ReferralCard,
  JourneyCard, AnswerActions, MinistryBadge,
} from "./AnswerBlocks";
import { Seal, Mark, FlagRibbon } from "./Brand";
import { Surface, Chip } from "./ui";
import { MinistryPicker } from "./MinistryPicker";

const EXAMPLES = [
  { q: "What are my rights under the data protection law?", icon: "shield" },
  { q: "How do I import a car from abroad?", icon: "directions_car" },
  { q: "What taxes do employers pay?", icon: "payments" },
  { q: "What is the National AI Strategy?", icon: "smart_toy" },
];

// Guided question sent when a journey tile is tapped (matches the journey keywords).
const JOURNEY_PROMPT: Record<string, string> = {
  lost_national_id: "How do I replace a lost national ID?",
  passport: "How do I apply for a passport?",
  tax_clearance: "How do I get a tax clearance certificate?",
  birth_certificate: "How do I register a birth certificate?",
  business_tax_registration: "How do I register a business for tax?",
  exam_results_certificate: "How do I check exam results or replace a certificate?",
};

let idCounter = 0;
const nextId = () => `m${++idCounter}`;

// Data-use consent (Data Protection Act [Chapter 12:07]): asking is blocked until
// the checkbox is ticked; the choice is stored client-side with a timestamp.
const CONSENT_KEY = "mambo_consent_v1";

interface Props {
  ministries: Ministry[];
  ministriesLoaded: boolean;
  selected: string | null;
  onSelect: (id: string | null) => void;
  chatStarted: boolean;
  onChatStart: () => void;
}

export function Chat({ ministries, ministriesLoaded, selected, onSelect, chatStarted, onChatStart }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [consented, setConsented] = useState(false);
  const [consentNudge, setConsentNudge] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const byId = useMemo(() => Object.fromEntries(ministries.map((m) => [m.id, m])) as Record<string, Ministry>, [ministries]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { try { if (localStorage.getItem(CONSENT_KEY)) setConsented(true); } catch { /* private mode */ } }, []);
  useEffect(() => { if (chatStarted && inputRef.current) inputRef.current.focus(); }, [chatStarted]);
  useEffect(() => () => abortRef.current?.abort(), []);

  function patch(id: string, fn: (m: ChatMessage) => ChatMessage) {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
  }

  function setConsent(on: boolean) {
    setConsented(on);
    setConsentNudge(false);
    try {
      if (on) localStorage.setItem(CONSENT_KEY, new Date().toISOString());
      else localStorage.removeItem(CONSENT_KEY);
    } catch { /* private mode */ }
  }

  async function send(question?: string) {
    const q = (question ?? input).trim();
    if (!q || busy) return;
    if (!consented) { setConsentNudge(true); return; }
    setInput("");
    setBusy(true);
    if (!chatStarted) onChatStart();

    const history = messages.filter((m) => !m.streaming && m.text).slice(-6).map((m) => ({ role: m.role, content: m.text }));
    const userMsg: ChatMessage = { id: nextId(), role: "user", text: q };
    const aId = nextId();
    const assistantMsg: ChatMessage = { id: aId, role: "assistant", text: "", streaming: true, steps: [] };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await askStream(q, selected, history, {
        onDelta: (t) => patch(aId, (m) => ({ ...m, text: m.text + t })),
        onStatus: (s) => patch(aId, (m) => ({ ...m, steps: [...(m.steps ?? []), s] })),
        onDone: (meta) => patch(aId, (m) => ({ ...m, streaming: false, meta })),
        onError: () => patch(aId, (m) => ({ ...m, streaming: false, text: m.text || "Sorry — I couldn't reach the service just now. Please try again in a moment." })),
      }, ctrl.signal);
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  const onAsk = (q: string) => send(q);

  if (!chatStarted) {
    return <Landing value={input} onChange={setInput} onAsk={onAsk} busy={busy}
      byId={byId} ministries={ministries} ministriesLoaded={ministriesLoaded} selected={selected} onSelect={onSelect}
      consented={consented} consentNudge={consentNudge} onConsent={setConsent} />;
  }

  return (
    <div className="flex flex-1 flex-col" style={{ minHeight: 0 }}>
      <div className="scroll-thin flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[44rem] px-4 py-5 sm:px-6 sm:py-8">
          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="mb-5 flex justify-end">
                <div className="max-w-[82%] rounded-2xl rounded-br-md px-4 py-2.5 text-[15px] leading-relaxed"
                  style={{ background: "var(--bg-user-bubble)", color: "var(--text-primary)" }}>{m.text}</div>
              </div>
            ) : (
              <div key={m.id} className="mb-5 animate-rise"><AssistantMessage m={m} byId={byId} /></div>
            ),
          )}
          <div ref={bottomRef} />
        </div>
      </div>
      <Composer value={input} onChange={setInput} onSend={() => send()} busy={busy}
        ministries={ministries} ministriesLoaded={ministriesLoaded} selected={selected} onSelect={onSelect} inputRef={inputRef} />
    </div>
  );
}

/* ─── Service-first Landing ─── */
function Landing({
  value, onChange, onAsk, busy, byId, ministries, ministriesLoaded, selected, onSelect,
  consented, consentNudge, onConsent,
}: {
  value: string; onChange: (v: string) => void; onAsk: (q: string) => void; busy: boolean;
  byId: Record<string, Ministry>; ministries: Ministry[]; ministriesLoaded: boolean;
  selected: string | null; onSelect: (id: string | null) => void;
  consented: boolean; consentNudge: boolean; onConsent: (on: boolean) => void;
}) {
  const canSend = !busy && !!value.trim() && ministriesLoaded;
  return (
    <div className="scroll-thin flex-1 overflow-y-auto">
      <div className="mx-auto w-full max-w-[44rem] px-4 py-8 sm:py-12 animate-fade-up">
        {/* Hero */}
        <div className="text-center mb-5">
          <div className="flex justify-center mb-3"><Seal size={56} glow /></div>
          <h1 className="font-display font-semibold leading-tight"
            style={{ color: "var(--text-primary)", fontSize: "clamp(26px, 5vw, 34px)" }}>
            What do you need to do today?
          </h1>
          <p className="mt-3 text-[15px] leading-relaxed max-w-lg mx-auto" style={{ color: "var(--text-secondary)" }}>
            Mambo answers in plain language using <strong style={{ color: "var(--text-primary)" }}>only retrieved source documents</strong> — with citations shown.
          </p>
          <p className="mt-3 flex items-center justify-center gap-4 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
            <span className="inline-flex items-center gap-1"><span className="material-symbols" style={{ fontSize: 14 }}>verified</span>Allow-listed sources</span>
            <span className="inline-flex items-center gap-1"><span className="material-symbols" style={{ fontSize: 14 }}>update</span>Kept current</span>
          </p>
        </div>
        <div className="mb-5"><FlagRibbon height={3} radius={2} /></div>

        {/* Free-ask composer (peer to the journeys) */}
        <div className="w-full mb-6">
          <Surface style={{ padding: 10 }}>
            <textarea value={value} onChange={(e) => onChange(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) onAsk(value); } }}
              rows={1} placeholder="Ask anything about government services…"
              className="w-full resize-none rounded-xl border-0 bg-transparent px-3 py-2 text-[16px] outline-none placeholder:text-[var(--text-tertiary)]"
              style={{ color: "var(--text-primary)", minHeight: 48, maxHeight: 160 }} autoFocus />
            <div className="flex items-center justify-between gap-2 px-1 pt-1">
              <MinistryPicker compact ministries={ministries} ministriesLoaded={ministriesLoaded} selected={selected} onSelect={onSelect} />
              <button onClick={() => canSend && onAsk(value)} disabled={!canSend}
                className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-white transition disabled:opacity-30 active:scale-[0.95]"
                style={{ background: "var(--grad-accent)" }} aria-label="Send">
                {busy ? <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
                  : <span className="material-symbols" style={{ fontSize: 20 }}>arrow_upward</span>}
              </button>
            </div>
          </Surface>
          <ConsentBox checked={consented} nudge={consentNudge} onChange={onConsent} />
          <p className="mt-2 text-center text-[11px]" style={{ color: "var(--text-tertiary)" }}>
            <kbd className="rounded border px-1 py-px text-[10px] font-mono" style={{ borderColor: "var(--border-primary)" }}>Enter</kbd> to send
          </p>
        </div>

        {/* Journey grid */}
        <div className="mb-2 text-[12px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>Common services</div>
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {JOURNEYS.map((j, i) => (
            <JourneyTile key={j.id} journey={j} byId={byId} index={i} onPick={() => onAsk(JOURNEY_PROMPT[j.id])} />
          ))}
        </div>

        {/* Examples */}
        <div className="mt-6 text-[12px] mb-2" style={{ color: "var(--text-tertiary)" }}>Or try a question:</div>
        <div className="flex flex-wrap gap-2">
          {EXAMPLES.map((ex) => (
            <Chip key={ex.q} onClick={() => onAsk(ex.q)}>
              <span className="material-symbols" style={{ fontSize: 14 }}>{ex.icon}</span>{ex.q}
            </Chip>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Data-use consent checkbox (DPA [Chapter 12:07]) ───
   Full box until consent is given; then it folds into one quiet line so
   returning visitors keep the notice without the visual weight. */
function ConsentBox({ checked, nudge, onChange }: {
  checked: boolean; nudge: boolean; onChange: (on: boolean) => void;
}) {
  if (checked) {
    return (
      <label className="mt-2 flex items-center justify-center gap-2 cursor-pointer px-2 animate-rise">
        <input type="checkbox" checked onChange={(e) => onChange(e.target.checked)}
          aria-describedby="consent-note" className="h-3.5 w-3.5 shrink-0 accent-[var(--accent)]" />
        <span id="consent-note" className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          Data-use consent given (DPA [Chapter 12:07]) — please don&apos;t include personal details.
        </span>
      </label>
    );
  }
  return (
    <div className={`mt-2${nudge ? " animate-shake" : ""}`}>
      <label className="flex items-start gap-2.5 rounded-xl px-3 py-2.5 cursor-pointer transition"
        style={{
          background: "var(--bg-secondary)",
          border: nudge ? "1.5px solid var(--red)" : "1px solid var(--border-light)",
        }}>
        <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)}
          aria-describedby="consent-note" className="mt-0.5 h-4 w-4 shrink-0 accent-[var(--accent)]" />
        <span id="consent-note" className="text-[12px] leading-relaxed" style={{ color: "var(--text-secondary)" }}>
          I agree that my question may be processed and stored in minimised form to answer it
          and improve the service (Data Protection Act [Chapter 12:07]).{" "}
          <strong style={{ color: "var(--text-primary)" }}>Please don&apos;t include personal details</strong> —
          ID numbers, phone numbers, or medical information.
        </span>
      </label>
      {nudge && (
        <p role="alert" className="mt-1.5 flex items-center gap-1 text-[12px] font-medium m-0" style={{ color: "var(--red)" }}>
          <span className="material-symbols" style={{ fontSize: 14 }}>error</span>
          Please tick the consent box before asking.
        </p>
      )}
    </div>
  );
}

function JourneyTile({ journey, byId, index, onPick }: {
  journey: { id: string; title: string; ministry: string; icon?: string };
  byId: Record<string, Ministry>; index: number; onPick: () => void;
}) {
  const color = byId[journey.ministry]?.accent_color || "#64748b";
  return (
    <button onClick={onPick}
      className="group flex flex-col gap-2 rounded-xl p-3.5 text-left transition active:scale-[0.98] animate-scale-in"
      style={{ background: "var(--bg-surface)", border: "1px solid var(--border-light)", boxShadow: "var(--shadow-sm)", animationDelay: `${index * 60}ms` }}>
      <span className="grid h-9 w-9 place-items-center rounded-lg" style={{ background: `${color}1f` }}>
        <span className="material-symbols" style={{ fontSize: 20, color }}>{journey.icon}</span>
      </span>
      <span className="text-[13.5px] font-semibold leading-snug font-display" style={{ color: "var(--text-primary)" }}>{journey.title}</span>
      <span className="flex items-center justify-between">
        <MinistryBadge id={journey.ministry} byId={byId} />
        <span className="material-symbols transition group-hover:translate-x-0.5" style={{ fontSize: 16, color: "var(--text-tertiary)" }}>arrow_forward</span>
      </span>
    </button>
  );
}

/* ─── Assistant message ─── */
function AssistantMessage({ m, byId }: { m: ChatMessage; byId: Record<string, Ministry> }) {
  const meta = m.meta;
  const ministries = meta?.source_ministry ?? [];
  const accent = ministries[0] ? (byId[ministries[0]]?.accent_color || "var(--accent)") : "var(--accent)";
  const journey = getJourney(meta?.service_journey);
  const steps = m.steps ?? [];
  const declined = meta?.evidence_status === "declined";
  const showBody = !(m.streaming && !m.text);

  return (
    <div style={{ ["--answer-accent" as string]: accent } as React.CSSProperties}>
      <div className="mb-2 flex items-center gap-2">
        <Mark size={24} />
        <span className="text-[13px] font-semibold font-display" style={{ color: "var(--text-primary)" }}>Mambo</span>
        {ministries.map((id) => <MinistryBadge key={id} id={id} byId={byId} />)}
      </div>

      {m.streaming && steps.length > 0 && <div className="mb-2"><ThinkingSteps steps={steps} done={false} /></div>}

      {meta && !m.streaming && <div className="mb-2"><EvidenceHeader status={meta.evidence_status} /></div>}
      {declined && meta?.decline_reason && !m.streaming && <div className="mb-2"><ReferralCard reason={meta.decline_reason} /></div>}

      {showBody && (
        <div aria-busy={m.streaming} aria-live="polite">
          {journey ? <JourneyCard text={m.text} journey={journey} byId={byId} />
            : <div className={m.streaming ? "caret" : ""}><AnswerText text={m.text} /></div>}
        </div>
      )}
      {m.streaming && !m.text && steps.length === 0 && <TypingDots />}

      {!m.streaming && meta && (
        <div className="mt-3 space-y-2">
          {meta.citations.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">{meta.citations.map((c, i) => <CitationCard key={i} c={c} index={i} byId={byId} />)}</div>
          )}
          {meta.fallback_contact?.map((c, i) => <ContactCard key={i} c={c} byId={byId} />)}
          {steps.length > 0 && <ThinkingSteps steps={steps} done={true} />}
          {!journey && <div className="flex justify-end pt-1"><AnswerActions text={m.text} /></div>}
        </div>
      )}
    </div>
  );
}

/* ─── Thinking steps (live, then collapsible) ─── */
const STEP_ICON: Record<string, string> = { route: "account_tree", search: "search", read: "menu_book", verify: "travel_explore" };
function ThinkingSteps({ steps, done }: { steps: StatusEvent[]; done: boolean }) {
  if (!steps.length) return null;
  const body = (
    <div className="space-y-1.5">
      {steps.map((s, i) => {
        const active = !done && i === steps.length - 1;
        return (
          <div key={i} className="flex items-center gap-2 animate-rise" style={{ animationDelay: `${i * 60}ms` }}>
            <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full"
              style={{ background: active ? "var(--accent-light)" : "transparent", border: `1px solid ${active ? "var(--accent)" : "var(--border-primary)"}` }}>
              {active
                ? <span className="h-2 w-2 rounded-full animate-pulse-soft" style={{ background: "var(--accent)" }} />
                : <span className="material-symbols" style={{ fontSize: 12, color: "var(--accent)" }}>check</span>}
            </span>
            <span className="inline-flex items-center gap-1.5 text-[12px]" style={{ color: active ? "var(--text-secondary)" : "var(--text-tertiary)" }}>
              <span className="material-symbols" style={{ fontSize: 13, color: "var(--text-tertiary)" }}>{STEP_ICON[s.step ?? ""] ?? "circle"}</span>
              {s.text}
            </span>
          </div>
        );
      })}
    </div>
  );
  if (done) {
    return (
      <details className="rounded-lg px-3 py-1.5" style={{ background: "var(--bg-secondary)" }}>
        <summary className="cursor-pointer text-[11px]" style={{ color: "var(--text-tertiary)" }}>How Mambo answered this</summary>
        <div className="mt-2">{body}</div>
      </details>
    );
  }
  return <div role="status" aria-live="polite">{body}</div>;
}

function TypingDots() {
  return (
    <div className="flex items-center gap-1.5 py-1" style={{ color: "var(--text-secondary)" }}>
      {[0, 1, 2].map((i) => (
        <span key={i} className="h-2 w-2 rounded-full animate-pulse-soft" style={{ background: "var(--accent)", animationDelay: `${i * 0.18}s` }} />
      ))}
      <span className="ml-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>searching official documents…</span>
    </div>
  );
}

/* ─── Composer ─── */
function Composer({
  value, onChange, onSend, busy, ministries, ministriesLoaded, selected, onSelect, inputRef,
}: {
  value: string; onChange: (v: string) => void; onSend: () => void; busy: boolean;
  ministries: Ministry[]; ministriesLoaded: boolean; selected: string | null; onSelect: (id: string | null) => void;
  inputRef: React.Ref<HTMLTextAreaElement>;
}) {
  const canSend = !busy && !!value.trim() && ministriesLoaded;
  return (
    <div className="border-t px-3 py-3 sm:px-4" style={{ borderColor: "var(--border-primary)", background: "var(--bg-primary)", paddingBottom: "calc(var(--safe-bottom) + 12px)" }}>
      <div className="mx-auto w-full max-w-[44rem]">
        <div className="flex items-end gap-2 rounded-2xl border px-3 py-2"
          style={{ borderColor: "var(--border-primary)", background: "var(--bg-secondary)", boxShadow: "var(--shadow-sm)" }}>
          <textarea ref={inputRef} value={value} onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); if (canSend) onSend(); } }}
            rows={1} placeholder="Ask a follow‑up…"
            className="flex-1 resize-none bg-transparent px-1 py-1.5 text-[15px] outline-none placeholder:text-[var(--text-tertiary)]"
            style={{ color: "var(--text-primary)", maxHeight: 160 }} />
          <button onClick={() => canSend && onSend()} disabled={!canSend}
            className="grid h-10 w-10 shrink-0 place-items-center rounded-xl text-white transition disabled:opacity-30 active:scale-[0.95]"
            style={{ background: "var(--grad-accent)" }} aria-label="Send">
            {busy ? <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              : <span className="material-symbols" style={{ fontSize: 18 }}>arrow_upward</span>}
          </button>
        </div>
        <div className="mt-2 flex items-center gap-2 overflow-x-auto scroll-thin px-0.5">
          <span className="text-[11px] shrink-0" style={{ color: "var(--text-tertiary)" }}>Focus:</span>
          <MinistryPicker compact ministries={ministries} ministriesLoaded={ministriesLoaded} selected={selected} onSelect={onSelect} />
        </div>
      </div>
    </div>
  );
}
