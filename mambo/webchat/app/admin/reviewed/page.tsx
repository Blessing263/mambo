"use client";

import { useEffect, useState } from "react";
import { createReviewed, deleteReviewed, getReviewed, updateReviewed } from "@/lib/adminApi";
import type { ReviewedAnswer } from "@/lib/types";
import { PrimaryButton, Surface } from "@/components/ui";

const inputCls =
  "w-full rounded-lg border bg-transparent px-3 py-2 text-[13px] outline-none focus:border-[var(--accent)]";

export default function ReviewedPage() {
  const [rows, setRows] = useState<ReviewedAnswer[]>([]);
  const [editing, setEditing] = useState<(Partial<ReviewedAnswer> & { citations?: any[] }) | null>(null);

  const refresh = () => getReviewed().then(setRows).catch(() => {});
  useEffect(() => {
    refresh();
    const q = new URLSearchParams(window.location.search).get("question");
    if (q) setEditing({ question: q, answer: "", citations: [] });
  }, []);

  async function save() {
    if (!editing?.question || !editing.answer) return;
    const cites = (editing.citations || []).map((c) => ({ url: c.url }));
    if (editing.id) {
      await updateReviewed(editing.id, { question: editing.question, answer: editing.answer, citations: cites });
    } else {
      await createReviewed({ question: editing.question, answer: editing.answer, citations: cites });
    }
    setEditing(null);
    refresh();
  }

  const citeText = (editing?.citations || []).map((c) => c.url).join("\n");

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-3">
        <h1 className="font-display text-[20px] font-semibold" style={{ color: "var(--text-primary)" }}>Reviewed answers</h1>
        <button onClick={() => setEditing({ question: "", answer: "", citations: [] })}
          className="rounded-lg border px-3 py-1.5 text-[12px] font-medium" style={{ borderColor: "var(--border-primary)", color: "var(--text-secondary)" }}>
          + New
        </button>
      </div>

      <Surface style={{ padding: 16 }}>
        {rows.length === 0 ? (
          <p className="py-3 text-[13px]" style={{ color: "var(--text-tertiary)" }}>
            No curated answers yet. When you curate a question, citizens who ask it get this vetted answer instantly (no AI call).
          </p>
        ) : (
          <ul className="divide-y" style={{ borderColor: "var(--border-light)" }}>
            {rows.map((r) => (
              <li key={r.id} className="flex items-start gap-3 py-3">
                <div className="min-w-0 flex-1">
                  <div className="text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>{r.question}</div>
                  <div className="mt-0.5 line-clamp-2 text-[12px]" style={{ color: "var(--text-secondary)" }}>{r.answer}</div>
                </div>
                <button onClick={async () => { await updateReviewed(r.id, { enabled: !r.enabled }); refresh(); }}
                  className="shrink-0 rounded-md px-2 py-1 text-[11px] font-semibold"
                  style={r.enabled ? { background: "var(--accent-light)", color: "var(--accent-text)" } : { background: "var(--bg-hover)", color: "var(--text-tertiary)" }}>
                  {r.enabled ? "Enabled" : "Disabled"}
                </button>
                <button onClick={() => setEditing(r)} className="shrink-0 rounded-md px-2 py-1 text-[11px]" style={{ color: "var(--text-secondary)" }}>Edit</button>
                <button onClick={async () => { await deleteReviewed(r.id); refresh(); }} className="shrink-0 rounded-md px-2 py-1 text-[11px]" style={{ color: "var(--red)" }}>Delete</button>
              </li>
            ))}
          </ul>
        )}
      </Surface>

      {editing && (
        <Surface style={{ padding: 16 }}>
          <h2 className="mb-3 font-display text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {editing.id ? "Edit" : "New"} reviewed answer
          </h2>
          <div className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Question (exact match — what citizens will ask)</span>
              <input value={editing.question || ""} onChange={(e) => setEditing({ ...editing, question: e.target.value })}
                className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} placeholder="How do I replace a lost national ID?" />
            </label>
            <label className="block">
              <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Vetted answer (use [1], [2] … for citations)</span>
              <textarea value={editing.answer || ""} onChange={(e) => setEditing({ ...editing, answer: e.target.value })} rows={7}
                className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} placeholder="**Eligibility**&#10;…" />
            </label>
            <label className="block">
              <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Source URLs (one per line)</span>
              <textarea value={citeText}
                onChange={(e) => setEditing({ ...editing, citations: e.target.value.split("\n").filter(Boolean).map((url) => ({ url })) })}
                rows={3} className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }}
                placeholder="https://www.moha.gov.zw/…" />
            </label>
            <div className="flex gap-2">
              <PrimaryButton onClick={save}>{editing.id ? "Save changes" : "Create"}</PrimaryButton>
              <button onClick={() => setEditing(null)} className="rounded-lg border px-4 py-2 text-[13px]" style={{ borderColor: "var(--border-primary)", color: "var(--text-secondary)" }}>Cancel</button>
            </div>
          </div>
        </Surface>
      )}
    </div>
  );
}
