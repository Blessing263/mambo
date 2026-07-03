"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getQueries, getStats } from "@/lib/adminApi";
import type { AdminQuery, AdminStats } from "@/lib/types";
import { Surface } from "@/components/ui";

function StatCard({ label, value, icon, accent }: { label: string; value: React.ReactNode; icon: string; accent?: string }) {
  return (
    <Surface style={{ padding: 14 }}>
      <div className="flex items-center gap-2">
        <span className="material-symbols" style={{ fontSize: 18, color: accent || "var(--accent)" }}>{icon}</span>
        <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>{label}</span>
      </div>
      <div className="mt-1 font-display text-[24px] font-semibold" style={{ color: "var(--text-primary)" }}>{value}</div>
    </Surface>
  );
}

function Card({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <Surface style={{ padding: 16 }}>
      <div className="mb-2 flex items-center gap-2">
        <span className="material-symbols" style={{ fontSize: 16, color: "var(--text-tertiary)" }}>{icon}</span>
        <h2 className="text-[13px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>{title}</h2>
      </div>
      {children}
    </Surface>
  );
}

const Empty = () => <p className="py-4 text-center text-[12px]" style={{ color: "var(--text-tertiary)" }}>No data yet.</p>;

export default function AdminDashboard() {
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [queries, setQueries] = useState<AdminQuery[]>([]);
  useEffect(() => { getStats(30).then(setStats).catch(() => {}); getQueries(15).then(setQueries).catch(() => {}); }, []);

  return (
    <div className="space-y-5">
      <h1 className="font-display text-[20px] font-semibold" style={{ color: "var(--text-primary)" }}>
        Dashboard <span className="text-[12px] font-normal" style={{ color: "var(--text-tertiary)" }}>· last 30 days</span>
      </h1>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard label="Questions" value={stats?.total ?? "—"} icon="forum" />
        <StatCard label="Answered" value={stats && stats.total ? `${Math.round((100 * stats.answered) / stats.total)}%` : "—"} icon="check_circle" />
        <StatCard label="Fallback" value={stats?.fallback_rate != null ? `${Math.round(100 * stats.fallback_rate)}%` : "—"} icon="help" accent="var(--gold)" />
        <StatCard label="Avg feedback" value={stats?.avg_feedback != null ? stats.avg_feedback.toFixed(2) : "—"} icon="thumbs_up_down" />
      </div>

      <Card title="Top unanswered — curate these" icon="priority_high">
        {(stats?.top_unanswered ?? []).length === 0 ? <Empty /> : (
          <ul className="divide-y" style={{ borderColor: "var(--border-light)" }}>
            {(stats?.top_unanswered ?? []).slice(0, 8).map((q, i) => (
              <li key={i} className="flex items-center gap-2 py-2">
                <span className="flex-1 truncate text-[13px]" style={{ color: "var(--text-primary)" }}>{q.question}</span>
                <span className="shrink-0 text-[11px]" style={{ color: "var(--text-tertiary)" }}>{q.count}×</span>
                <Link href={`/admin/reviewed?question=${encodeURIComponent(q.question)}`}
                  className="shrink-0 rounded-md px-2 py-1 text-[11px] font-semibold transition hover:opacity-90"
                  style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}>Curate →</Link>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card title="Recent questions" icon="history">
        {queries.length === 0 ? <Empty /> : (
          <ul className="divide-y" style={{ borderColor: "var(--border-light)" }}>
            {queries.map((q, i) => (
              <li key={i} className="flex items-center gap-3 py-2">
                <div className="min-w-0 flex-1">
                  <div className="truncate text-[13px]" style={{ color: "var(--text-primary)" }}>{q.question}</div>
                  <div className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{q.asked_at ? new Date(q.asked_at).toLocaleString() : ""}</div>
                </div>
                <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold"
                  style={q.confident ? { background: "var(--accent-light)", color: "var(--accent-text)" } : { background: "var(--gold-light)", color: "var(--gold)" }}>
                  {q.confident ? "answered" : "fallback"}
                </span>
                <span className="w-5 shrink-0 text-center text-[12px]">{q.feedback ? (q.feedback > 0 ? "👍" : "👎") : ""}</span>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </div>
  );
}
