"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getQuestions } from "@/lib/adminApi";
import type { AdminQuestion } from "@/lib/types";
import { Surface } from "@/components/ui";

const statuses = [
  { value: "", label: "All" },
  { value: "unsupported", label: "Unsupported" },
  { value: "partial", label: "Partial" },
  { value: "declined", label: "Declined" },
  { value: "answered", label: "Answered" },
];

const badge: Record<string, { label: string; bg: string; color: string }> = {
  answered: { label: "Answered", bg: "var(--accent-light)", color: "var(--accent-text)" },
  partial: { label: "Partial", bg: "var(--gold-light)", color: "var(--gold)" },
  unsupported: { label: "Unsupported", bg: "var(--red-light)", color: "var(--red)" },
  declined: { label: "Declined", bg: "var(--bg-hover)", color: "var(--text-secondary)" },
};

export default function QuestionInboxPage() {
  const [rows, setRows] = useState<AdminQuestion[]>([]);
  const [q, setQ] = useState("");
  const [status, setStatus] = useState("");

  function refresh(nextQ = q, nextStatus = status) {
    getQuestions(80, 0, nextQ, nextStatus).then(setRows).catch(() => {});
  }

  useEffect(() => { refresh("", ""); }, []);

  function updateSearch(value: string) {
    setQ(value);
    refresh(value, status);
  }

  function updateStatus(value: string) {
    setStatus(value);
    refresh(q, value);
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="font-display text-[20px] font-semibold" style={{ color: "var(--text-primary)" }}>Question inbox</h1>
          <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
            Triage citizen demand and promote repeated gaps into official responses.
          </p>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <input
            value={q}
            onChange={(e) => updateSearch(e.target.value)}
            type="search"
            placeholder="Search questions"
            className="h-9 w-56 rounded-lg border bg-transparent px-3 text-[12px] outline-none focus:border-[var(--accent)]"
            style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }}
          />
          <select
            value={status}
            onChange={(e) => updateStatus(e.target.value)}
            className="h-9 rounded-lg border bg-transparent px-3 text-[12px] outline-none focus:border-[var(--accent)]"
            style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }}
          >
            {statuses.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>
        </div>
      </div>

      <Surface style={{ padding: 16 }}>
        {rows.length === 0 ? (
          <p className="py-6 text-center text-[13px]" style={{ color: "var(--text-tertiary)" }}>No matching questions.</p>
        ) : (
          <ul className="divide-y" style={{ borderColor: "var(--border-light)" }}>
            {rows.map((r) => {
              const b = badge[r.evidence_status] ?? badge.unsupported;
              return (
                <li key={r.id} className="grid gap-3 py-3 md:grid-cols-[1fr_auto] md:items-center">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ background: b.bg, color: b.color }}>
                        {b.label}
                      </span>
                      {r.reviewed && (
                        <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}>
                          Official
                        </span>
                      )}
                      <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                        {r.asked_at ? new Date(r.asked_at).toLocaleString() : ""}
                      </span>
                    </div>
                    <p className="mt-1 text-[13px] font-medium" style={{ color: "var(--text-primary)" }}>{r.question}</p>
                    <p className="mt-0.5 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
                      Feedback: {r.feedback == null ? "none" : r.feedback > 0 ? "helpful" : "not helpful"} · Latency: {r.latency_ms ? `${(r.latency_ms / 1000).toFixed(1)}s` : "n/a"}
                    </p>
                  </div>
                  <Link
                    href={`/admin/responses?question=${encodeURIComponent(r.question)}`}
                    className="inline-flex h-9 items-center justify-center rounded-lg px-3 text-[12px] font-semibold transition hover:opacity-90"
                    style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}
                  >
                    Draft response
                  </Link>
                </li>
              );
            })}
          </ul>
        )}
      </Surface>
    </div>
  );
}
