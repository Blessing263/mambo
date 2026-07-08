"use client";

import { useEffect, useState } from "react";
import {
  approveOfficialResponse,
  archiveOfficialResponse,
  createOfficialResponse,
  getOfficialResponses,
  submitOfficialResponse,
  updateOfficialResponse,
} from "@/lib/adminApi";
import type { OfficialResponse, OfficialResponseStatus } from "@/lib/types";
import { PrimaryButton, Surface } from "@/components/ui";

const inputCls =
  "w-full rounded-lg border bg-transparent px-3 py-2 text-[13px] outline-none focus:border-[var(--accent)]";

const tabs: { value: "" | OfficialResponseStatus; label: string }[] = [
  { value: "", label: "All" },
  { value: "draft", label: "Draft" },
  { value: "pending_review", label: "Pending" },
  { value: "approved", label: "Approved" },
  { value: "archived", label: "Archived" },
];

const statusStyle: Record<OfficialResponseStatus, { label: string; bg: string; color: string }> = {
  draft: { label: "Draft", bg: "var(--bg-hover)", color: "var(--text-secondary)" },
  pending_review: { label: "Pending review", bg: "var(--gold-light)", color: "var(--gold)" },
  approved: { label: "Approved", bg: "var(--accent-light)", color: "var(--accent-text)" },
  archived: { label: "Archived", bg: "var(--red-light)", color: "var(--red)" },
};

type Editing = Partial<OfficialResponse> & { citationText?: string; change_note?: string };

function toCitationText(citations: any[] | undefined) {
  return (citations || []).map((c) => [c.title, c.url].filter(Boolean).join(" | ")).join("\n");
}

function parseCitations(text: string) {
  return text.split("\n").map((line) => line.trim()).filter(Boolean).map((line) => {
    const [title, url] = line.includes("|") ? line.split("|").map((p) => p.trim()) : ["", line];
    return { title: title || undefined, url };
  });
}

export default function OfficialResponsesPage() {
  const [rows, setRows] = useState<OfficialResponse[]>([]);
  const [status, setStatus] = useState<"" | OfficialResponseStatus>("");
  const [q, setQ] = useState("");
  const [editing, setEditing] = useState<Editing | null>(null);
  const [error, setError] = useState("");

  function refresh(nextStatus = status, nextQ = q) {
    getOfficialResponses(nextStatus, nextQ).then(setRows).catch(() => {});
  }

  useEffect(() => {
    refresh("", "");
    const question = new URLSearchParams(window.location.search).get("question");
    if (question) setEditing({ question, answer: "", citations: [], citationText: "", status: "draft" });
  }, []);

  function openEdit(row: OfficialResponse) {
    setError("");
    setEditing({ ...row, citationText: toCitationText(row.citations), change_note: "" });
  }

  async function save() {
    if (!editing?.question || !editing.answer) return;
    setError("");
    const citations = parseCitations(editing.citationText || "");
    try {
      if (editing.id) {
        await updateOfficialResponse(editing.id, {
          question: editing.question,
          answer: editing.answer,
          citations,
          service_area: editing.service_area || null,
          enabled: editing.enabled,
          change_note: editing.change_note || "Updated in admin portal",
        });
      } else {
        await createOfficialResponse({
          question: editing.question,
          answer: editing.answer,
          citations,
          service_area: editing.service_area || null,
          status: "draft",
        });
      }
      setEditing(null);
      refresh();
    } catch (e: any) {
      setError(e?.message || "Could not save response");
    }
  }

  async function action(id: string, fn: (id: string) => Promise<OfficialResponse>) {
    setError("");
    try {
      await fn(id);
      refresh();
    } catch (e: any) {
      setError(e?.message || "Action failed");
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="font-display text-[20px] font-semibold" style={{ color: "var(--text-primary)" }}>Official responses</h1>
          <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
            Draft ministry-approved answers and publish them into the instant-answer and RAG pipeline.
          </p>
        </div>
        <div className="ml-auto flex flex-wrap gap-2">
          <input
            value={q}
            onChange={(e) => { setQ(e.target.value); refresh(status, e.target.value); }}
            type="search"
            placeholder="Search responses"
            className="h-9 w-56 rounded-lg border bg-transparent px-3 text-[12px] outline-none focus:border-[var(--accent)]"
            style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }}
          />
          <button
            onClick={() => setEditing({ question: "", answer: "", citations: [], citationText: "", status: "draft", enabled: true })}
            className="h-9 rounded-lg border px-3 text-[12px] font-semibold"
            style={{ borderColor: "var(--border-primary)", color: "var(--text-secondary)" }}
          >
            New response
          </button>
        </div>
      </div>

      <div className="flex flex-wrap gap-1">
        {tabs.map((t) => (
          <button
            key={t.value}
            onClick={() => { setStatus(t.value); refresh(t.value, q); }}
            className="rounded-lg px-3 py-1.5 text-[12px] font-medium"
            style={status === t.value ? { background: "var(--accent-light)", color: "var(--accent-text)" } : { color: "var(--text-secondary)" }}
          >
            {t.label}
          </button>
        ))}
      </div>

      {error && <p className="text-[12px]" style={{ color: "var(--red)" }}>{error}</p>}

      <div className="grid gap-4 lg:grid-cols-[minmax(0,1fr)_420px]">
        <Surface style={{ padding: 16 }}>
          {rows.length === 0 ? (
            <p className="py-6 text-center text-[13px]" style={{ color: "var(--text-tertiary)" }}>No official responses yet.</p>
          ) : (
            <ul className="divide-y" style={{ borderColor: "var(--border-light)" }}>
              {rows.map((r) => {
                const s = statusStyle[r.status];
                return (
                  <li key={r.id} className="py-3">
                    <div className="flex flex-wrap items-center gap-2">
                      <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold" style={{ background: s.bg, color: s.color }}>{s.label}</span>
                      {r.service_area && <span className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{r.service_area}</span>}
                      <span className="ml-auto text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                        {r.updated_at ? new Date(r.updated_at).toLocaleString() : ""}
                      </span>
                    </div>
                    <h2 className="mt-1 text-[13px] font-semibold" style={{ color: "var(--text-primary)" }}>{r.question}</h2>
                    <p className="mt-0.5 line-clamp-2 text-[12px]" style={{ color: "var(--text-secondary)" }}>{r.answer}</p>
                    <div className="mt-2 flex flex-wrap gap-2">
                      <button onClick={() => openEdit(r)} className="rounded-md px-2 py-1 text-[11px]" style={{ color: "var(--text-secondary)" }}>Edit</button>
                      {r.status === "draft" && <button onClick={() => action(r.id, submitOfficialResponse)} className="rounded-md px-2 py-1 text-[11px]" style={{ color: "var(--gold)" }}>Submit</button>}
                      {r.status !== "approved" && r.status !== "archived" && <button onClick={() => action(r.id, approveOfficialResponse)} className="rounded-md px-2 py-1 text-[11px] font-semibold" style={{ color: "var(--accent)" }}>Approve</button>}
                      {r.status !== "archived" && <button onClick={() => action(r.id, archiveOfficialResponse)} className="rounded-md px-2 py-1 text-[11px]" style={{ color: "var(--red)" }}>Archive</button>}
                    </div>
                  </li>
                );
              })}
            </ul>
          )}
        </Surface>

        {editing ? (
          <Surface style={{ padding: 16 }}>
            <h2 className="font-display text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>
              {editing.id ? "Edit response" : "New response"}
            </h2>
            <div className="mt-3 space-y-3">
              <label className="block">
                <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Service area</span>
                <input value={editing.service_area || ""} onChange={(e) => setEditing({ ...editing, service_area: e.target.value })}
                  className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} placeholder="Passport, National ID, Tax clearance" />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Citizen question</span>
                <input value={editing.question || ""} onChange={(e) => setEditing({ ...editing, question: e.target.value })}
                  className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Official answer</span>
                <textarea value={editing.answer || ""} onChange={(e) => setEditing({ ...editing, answer: e.target.value })} rows={10}
                  className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} />
              </label>
              <label className="block">
                <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Citations, one per line: title | URL</span>
                <textarea value={editing.citationText || ""} onChange={(e) => setEditing({ ...editing, citationText: e.target.value })} rows={4}
                  className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} />
              </label>
              {editing.id && (
                <label className="flex items-center gap-2 text-[12px]" style={{ color: "var(--text-secondary)" }}>
                  <input type="checkbox" checked={editing.enabled ?? true} onChange={(e) => setEditing({ ...editing, enabled: e.target.checked })} />
                  Enabled for citizen answers
                </label>
              )}
              {editing.id && (
                <label className="block">
                  <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>Change note</span>
                  <input value={editing.change_note || ""} onChange={(e) => setEditing({ ...editing, change_note: e.target.value })}
                    className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} placeholder="Updated fees, corrected source, etc." />
                </label>
              )}
              <div className="flex flex-wrap gap-2">
                <PrimaryButton onClick={save}>{editing.id ? "Save changes" : "Create draft"}</PrimaryButton>
                <button onClick={() => setEditing(null)} className="rounded-lg border px-4 py-2 text-[13px]" style={{ borderColor: "var(--border-primary)", color: "var(--text-secondary)" }}>Cancel</button>
              </div>
            </div>
          </Surface>
        ) : (
          <Surface style={{ padding: 16 }}>
            <h2 className="font-display text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>Publishing pipeline</h2>
            <ol className="mt-3 space-y-3 text-[12px]" style={{ color: "var(--text-secondary)" }}>
              <li><strong>Draft:</strong> write a ministry answer from a citizen question.</li>
              <li><strong>Submit:</strong> mark it ready for official review.</li>
              <li><strong>Approve:</strong> publish it to instant answers and semantic RAG retrieval.</li>
              <li><strong>Archive:</strong> remove stale guidance without deleting history.</li>
            </ol>
          </Surface>
        )}
      </div>
    </div>
  );
}
