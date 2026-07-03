"use client";

import { useEffect, useRef, useState, useMemo } from "react";
import { askStream } from "@/lib/api";
import type { ChatMessage, Ministry } from "@/lib/types";
import { AnswerText, CitationCard, ContactCard, EvidenceBadge } from "./AnswerBlocks";
import { MinistryPicker } from "./MinistryPicker";

const EXAMPLES = [
  { q: "What are my rights under the data protection law?", icon: "shield" },
  { q: "How do I import a car from abroad?", icon: "directions_car" },
  { q: "What taxes do employers need to pay?", icon: "payments" },
  { q: "What is the National AI Strategy?", icon: "smart_toy" },
  { q: "How do I renew my passport?", icon: "travel" },
  { q: "What support is there for ICT in schools?", icon: "school" },
];

let idCounter = 0;
const nextId = () => `m${++idCounter}`;

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
  const abortRef = useRef<AbortController | null>(null);
  const bottomRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const byId = useMemo(() => Object.fromEntries(ministries.map((m) => [m.id, m])), [ministries]);

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);
  useEffect(() => { if (chatStarted && inputRef.current) inputRef.current.focus(); }, [chatStarted]);

  // Cancel any in-flight stream on unmount so we don't try to setState after
  // the component is gone.
  useEffect(() => () => abortRef.current?.abort(), []);

  function patch(id: string, fn: (m: ChatMessage) => ChatMessage) {
    setMessages((prev) => prev.map((m) => (m.id === id ? fn(m) : m)));
  }

  async function send(question: string) {
    const q = question.trim();
    if (!q || busy) return;
    setInput("");
    setBusy(true);
    if (!chatStarted) onChatStart();

    const history = messages.filter((m) => !m.streaming && m.text).slice(-6)
      .map((m) => ({ role: m.role, content: m.text }));

    const userMsg: ChatMessage = { id: nextId(), role: "user", text: q };
    const aId = nextId();
    const assistantMsg: ChatMessage = { id: aId, role: "assistant", text: "", streaming: true };
    setMessages((prev) => [...prev, userMsg, assistantMsg]);

    const ctrl = new AbortController();
    abortRef.current = ctrl;
    try {
      await askStream(
        q,
        selected,
        history,
        {
          onDelta: (t) => patch(aId, (m) => ({ ...m, text: m.text + t })),
          onDone: (meta) => patch(aId, (m) => ({ ...m, streaming: false, meta })),
          onError: () => patch(aId, (m) => ({
            ...m,
            streaming: false,
            text: m.text || "Sorry — I couldn't reach the service just now. Please try again in a moment.",
          })),
        },
        ctrl.signal,
      );
    } finally {
      setBusy(false);
      abortRef.current = null;
    }
  }

  if (!chatStarted) {
    return <Landing value={input} onChange={setInput} onSend={() => send(input)} busy={busy}
      ministries={ministries} ministriesLoaded={ministriesLoaded} selected={selected} onSelect={onSelect} />;
  }

  return (
    <div className="flex flex-1 flex-col" style={{ minHeight: 0 }}>
      {/* Messages — full width with comfortable text measure */}
      <div className="scroll-thin flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-[44rem] px-4 py-5 sm:px-6 sm:py-8">
          {messages.map((m) =>
            m.role === "user" ? (
              <div key={m.id} className="mb-5 flex justify-end">
                <div className="max-w-[82%] rounded-2xl rounded-br-md px-4 py-2.5 text-[15px] leading-relaxed"
                  style={{ background: "var(--bg-user-bubble)", color: "var(--text-primary)" }}>
                  {m.text}
                </div>
              </div>
            ) : (
              <div key={m.id} className="mb-5">
                <AssistantMessage m={m} byId={byId} />
              </div>
            ),
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Composer — sticky bottom */}
      <Composer value={input} onChange={setInput} onSend={() => send(input)} busy={busy}
        ministries={ministries} ministriesLoaded={ministriesLoaded} selected={selected} onSelect={onSelect} inputRef={inputRef} />
    </div>
  );
}

/* ─── Landing State ─── */
function Landing({
  value, onChange, onSend, busy, ministries, ministriesLoaded, selected, onSelect,
}: {
  value: string; onChange: (v: string) => void; onSend: () => void; busy: boolean;
  ministries: Ministry[]; ministriesLoaded: boolean; selected: string | null; onSelect: (id: string | null) => void;
}) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center px-4 pb-10 pt-10 sm:pt-14 animate-fade-up">
      {/* Hero */}
      <div className="mb-8 text-center max-w-2xl">
        <span style={{ fontSize: 48 }}>🇿🇼</span>
        <h1 className="mt-3 text-[28px] font-semibold tracking-tight leading-tight sm:text-[34px]"
          style={{ color: "var(--text-primary)" }}>
          Ask the Government of Zimbabwe
        </h1>
        <p className="mt-3 text-[15px] leading-relaxed max-w-lg mx-auto" style={{ color: "var(--text-secondary)" }}>
          Mambo answers in plain language using <strong style={{ color: "var(--text-primary)" }}>only official ministry documents</strong>.
          Every answer shows its source — free, day and night, on any device.
        </p>
        <p className="mt-3 flex items-center justify-center gap-3 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
          <span className="inline-flex items-center gap-1">
            <span className="material-symbols" style={{ fontSize: 14 }}>description</span>
            902 documents from 8 official sources
          </span>
          <span className="inline-flex items-center gap-1">
            <span className="material-symbols" style={{ fontSize: 14 }}>update</span>
            Updated 8 June 2026
          </span>
        </p>
      </div>

      {/* Prompt box */}
      <div className="w-full max-w-[42rem]">
        <div className="rounded-2xl border p-2.5 shadow-md" style={{ borderColor: "var(--border-primary)", background: "var(--bg-surface)", boxShadow: "var(--shadow-md)" }}>
          <textarea
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); }
            }}
            rows={1}
            placeholder="Ask a question in plain language…"
            className="w-full resize-none rounded-xl border-0 bg-transparent px-3 py-2 text-[16px] outline-none placeholder:text-[var(--text-tertiary)]"
            style={{ color: "var(--text-primary)", minHeight: 48, maxHeight: 180 }}
            autoFocus
          />
          <div className="flex items-center justify-between gap-2 px-1">
            <MinistryPicker compact ministries={ministries} ministriesLoaded={ministriesLoaded} selected={selected} onSelect={onSelect} />
            <button
              onClick={onSend}
              disabled={busy || !value.trim() || !ministriesLoaded}
              className="grid h-9 w-9 shrink-0 place-items-center rounded-xl text-white transition disabled:opacity-30 hover:opacity-90 active:scale-[0.95]"
              style={{ background: "var(--accent)" }}
              aria-label="Send"
            >
              {busy ? (
                <span className="h-4 w-4 animate-spin rounded-full border-2 border-white/40 border-t-white" />
              ) : (
                <span className="material-symbols" style={{ fontSize: 20 }}>arrow_upward</span>
              )}
            </button>
          </div>
        </div>
        <p className="mt-2 text-center text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          <span className="inline-flex items-center gap-0.5">
            <kbd className="rounded border px-1 py-px text-[10px] font-mono" style={{ borderColor: "var(--border-primary)" }}>Enter</kbd> to send · <kbd className="rounded border px-1 py-px text-[10px] font-mono" style={{ borderColor: "var(--border-primary)" }}>Shift</kbd>+<kbd className="rounded border px-1 py-px text-[10px] font-mono" style={{ borderColor: "var(--border-primary)" }}>Enter</kbd> for new line
          </span>
        </p>
      </div>

      {/* Quick examples */}
      <div className="mt-5 w-full max-w-[44rem]">
        <div className="grid gap-2.5 sm:grid-cols-2 lg:grid-cols-3">
          {EXAMPLES.map((ex) => (
            <button
              key={ex.q}
              onClick={() => { onChange(ex.q); onSend(); }}
              className="group flex items-start gap-2.5 rounded-xl border px-3.5 py-3 text-left transition active:scale-[0.98]"
              style={{ borderColor: "var(--border-light)", background: "var(--bg-surface)", boxShadow: "var(--shadow-sm)" }}
            >
              <span className="material-symbols mt-0.5 shrink-0" style={{ fontSize: 18, color: "var(--text-tertiary)" }}>
                {ex.icon}
              </span>
              <span className="text-[13px] leading-snug" style={{ color: "var(--text-secondary)" }}>{ex.q}</span>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

/* ─── Assistant message ─── */
function AssistantMessage({ m, byId }: { m: ChatMessage; byId: Record<string, Ministry> }) {
  const meta = m.meta;
  const ministries = meta?.source_ministry ?? [];
  return (
    <div>
      {/* Avatar row */}
      <div className="mb-2 flex items-center gap-2">
        <span className="grid h-6 w-6 place-items-center rounded-lg text-[10px] font-bold text-white shrink-0" style={{ background: "var(--accent)" }}>R</span>
        <span className="text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>Mambo</span>
        {ministries.map((id) => (
          <span key={id} className="rounded-full px-2 py-0.5 text-[10px] font-medium"
            style={{ background: `${byId[id]?.accent_color ?? "#64748b"}18`, color: byId[id]?.accent_color ?? "#64748b" }}>
            {byId[id]?.short_name ?? id}
          </span>
        ))}
      </div>

      {/* Body */}
      {m.streaming && !m.text ? (
        <TypingDots />
      ) : (
        <div className={m.streaming ? "caret" : ""}>
          <AnswerText text={m.text} />
        </div>
      )}

      {/* Sources + footer */}
      {!m.streaming && meta && (
        <div className="mt-3 space-y-2">
          {meta.citations.length > 0 && (
            <div className="grid gap-2 sm:grid-cols-2">
              {meta.citations.map((c, i) => <CitationCard key={i} c={c} byId={byId} />)}
            </div>
          )}
          {meta.fallback_contact?.map((c, i) => <ContactCard key={i} c={c} />)}
          <Footer answerText={m.text} meta={meta} />
        </div>
      )}
    </div>
  );
}

function Footer({ answerText, meta }: { answerText: string; meta: NonNullable<ChatMessage["meta"]> }) {
  const [fb, setFb] = useState<1 | -1 | null>(null);
  const [copied, setCopied] = useState(false);
  function onCopy() {
    navigator.clipboard.writeText(answerText).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); }).catch(() => {});
  }
  return (
    <div className="flex items-center justify-between pt-2" style={{ color: "var(--text-tertiary)", fontSize: 11 }}>
      <EvidenceBadge status={meta.evidence_status} />
      <span className="flex gap-0.5">
        <button aria-label="Copy answer" onClick={onCopy}
          className="rounded p-1 transition hover:text-[var(--text-primary)]"
          style={{ color: copied ? "var(--accent)" : undefined }}>
          <span className="material-symbols" style={{ fontSize: 16 }}>{copied ? "check" : "content_copy"}</span>
        </button>
        {([1, -1] as const).map((v) => {
          const label = v === 1 ? "Helpful" : "Not helpful";
          const sym = v === 1 ? "thumb_up" : "thumb_down";
          return (
            <button key={v} aria-label={label} onClick={() => setFb(fb === v ? null : v)}
              className="rounded p-1 transition"
              style={{ color: fb === v ? (v === 1 ? "var(--accent)" : "var(--red)") : undefined }}>
              <span className="material-symbols" style={{ fontSize: 16 }}>{sym}</span>
            </button>
          );
        })}
      </span>
    </div>
  );
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
  return (
    <div className="border-t px-3 py-3 sm:px-4" style={{ borderColor: "var(--border-primary)", background: "var(--bg-primary)" }}>
      <div className="mx-auto w-full max-w-[44rem]">
        <div className="flex items-end gap-2 rounded-2xl border px-3 py-2" style={{ borderColor: "var(--border-primary)", background: "var(--bg-secondary)", boxShadow: "var(--shadow-sm)" }}>
          <textarea
            ref={inputRef}
            value={value}
            onChange={(e) => onChange(e.target.value)}
            onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); onSend(); } }}
            rows={1}
            placeholder="Ask a follow‑up…"
            className="flex-1 resize-none bg-transparent px-1 py-1.5 text-[15px] outline-none placeholder:text-[var(--text-tertiary)]"
            style={{ color: "var(--text-primary)", maxHeight: 160 }}
          />
          <button onClick={onSend} disabled={busy || !value.trim() || !ministriesLoaded}
            className="grid h-8 w-8 shrink-0 place-items-center rounded-lg text-white transition disabled:opacity-30 active:scale-[0.95]"
            style={{ background: "var(--accent)" }} aria-label="Send">
            {busy ? (
              <span className="h-3.5 w-3.5 animate-spin rounded-full border-2 border-white/40 border-t-white" />
            ) : (
              <span className="material-symbols" style={{ fontSize: 18 }}>arrow_upward</span>
            )}
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
