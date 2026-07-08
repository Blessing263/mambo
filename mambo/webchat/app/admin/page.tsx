"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { getMe, getQueries, getStats } from "@/lib/adminApi";
import type { AdminQuery, AdminStats, Staff } from "@/lib/types";
import { Surface } from "@/components/ui";

function StatCard({ label, value, icon, accent }: { label: string; value: React.ReactNode; icon: string; accent?: string }) {
  return (
    <Surface style={{ padding: 14 }}>
      <div className="flex items-center gap-2">
        <span className="material-symbols" style={{ fontSize: 18, color: accent || "var(--accent)" }} aria-hidden="true">{icon}</span>
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
        <span className="material-symbols" style={{ fontSize: 16, color: "var(--text-tertiary)" }} aria-hidden="true">{icon}</span>
        <h2 className="text-[13px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-secondary)" }}>{title}</h2>
      </div>
      {children}
    </Surface>
  );
}

const Empty = () => <p className="py-4 text-center text-[12px]" style={{ color: "var(--text-tertiary)" }}>No data yet.</p>;

function BarChart({ series }: { series: { day: string | null; count: number }[] }) {
  if (!series.length) return <Empty />;
  const max = Math.max(...series.map((s) => s.count));
  const today = new Date();
  const days: { label: string; day: string; count: number }[] = [];
  for (let i = 29; i >= 0; i--) {
    const d = new Date(today);
    d.setDate(d.getDate() - i);
    const key = d.toISOString().slice(0, 10);
    const hit = series.find((s) => s.day?.startsWith(key));
    days.push({
      label: d.toLocaleDateString("en", { weekday: "short" }),
      day: d.toLocaleDateString("en", { day: "numeric", month: "short" }),
      count: hit ? hit.count : 0,
    });
  }
  return (
    <div className="flex items-end gap-[3px]" style={{ height: 120 }} aria-label="Daily question chart">
      {days.map((d, i) => (
        <div key={i} className="flex flex-1 flex-col items-center" title={`${d.day}: ${d.count} questions`}>
          <span className="mb-0.5 text-[9px]" style={{ color: "var(--text-tertiary)" }}>{d.count || ""}</span>
          <div
            className="w-full rounded-t-sm transition-all"
            style={{
              height: max > 0 ? `${Math.max(4, (d.count / max) * 100)}%` : "4px",
              background: d.count > 0 ? "var(--grad-accent)" : "var(--border-light)",
              minHeight: 4,
            }}
          />
          <span className="mt-1 text-[8px] uppercase" style={{ color: "var(--text-tertiary)" }}>{d.label.slice(0, 3)}</span>
        </div>
      ))}
    </div>
  );
}

const issueCards = [
  { key: "coverage_gap", label: "Coverage gaps", icon: "playlist_add", href: "/admin/questions?issue=coverage_gap", accent: "var(--gold)" },
  { key: "quality_issue", label: "Poor feedback", icon: "thumb_down", href: "/admin/questions?issue=quality_issue", accent: "var(--red)" },
  { key: "safety_escalation", label: "Declined/safety", icon: "policy", href: "/admin/questions?issue=safety_escalation", accent: "var(--red)" },
  { key: "official_answer", label: "Official answers", icon: "verified", href: "/admin/questions?issue=official_answer", accent: "var(--accent)" },
];

function RolePanel({ staff, stats }: { staff: Staff | null; stats: AdminStats | null }) {
  const role = staff?.role || "agent";
  const pending = stats?.response_counts?.pending_review ?? 0;
  const draft = stats?.response_counts?.draft ?? 0;
  const agent = role !== "supervisor";
  return (
    <Card title={agent ? "Agent desk" : "Supervisor desk"} icon={agent ? "support_agent" : "admin_panel_settings"}>
      <div className="space-y-3 text-[13px]" style={{ color: "var(--text-secondary)" }}>
        <p>
          {agent
            ? "Triage citizen issues for your ministry, draft official responses, and keep handoff details current."
            : "Review pending official responses, approve ministry guidance, and watch quality or safety escalations."}
        </p>
        <div className="grid grid-cols-2 gap-2">
          <Link href="/admin/questions?issue=coverage_gap" className="rounded-lg border px-3 py-2 text-[12px] font-semibold" style={{ borderColor: "var(--border-primary)", color: "var(--text-secondary)" }}>
            Triage gaps
          </Link>
          <Link href={agent ? "/admin/responses?status=draft" : "/admin/responses?status=pending_review"} className="rounded-lg border px-3 py-2 text-[12px] font-semibold" style={{ borderColor: "var(--border-primary)", color: "var(--text-secondary)" }}>
            {agent ? `${draft} drafts` : `${pending} pending`}
          </Link>
        </div>
      </div>
    </Card>
  );
}

export default function AdminDashboard() {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [stats, setStats] = useState<AdminStats | null>(null);
  const [queries, setQueries] = useState<AdminQuery[]>([]);

  useEffect(() => {
    getMe().then(setStaff).catch(() => {});
    getStats(30).then(setStats).catch(() => {});
    getQueries(10).then(setQueries).catch(() => {});
  }, []);

  const tokenK = stats && stats.token_count > 0 ? `${(stats.token_count / 1000).toFixed(1)}K` : "-";

  return (
    <div className="space-y-5">
      <div className="flex flex-wrap items-end gap-3">
        <div>
          <h1 className="font-display text-[22px] font-semibold" style={{ color: "var(--text-primary)" }}>Command centre</h1>
          <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
            {staff?.ministry_short_name || "Ministry"} work queue, official guidance, and citizen demand over the last 30 days.
          </p>
        </div>
        <Link href="/admin/responses" className="ml-auto inline-flex h-9 items-center rounded-lg px-3 text-[12px] font-semibold" style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}>
          Manage responses
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4 lg:grid-cols-6">
        <StatCard label="Questions" value={stats?.total ?? "-"} icon="forum" />
        <StatCard label="Answered" value={stats && stats.total ? `${Math.round((100 * stats.answered) / stats.total)}%` : "-"} icon="check_circle" />
        <StatCard label="Fallback" value={stats?.fallback_rate != null ? `${Math.round(100 * stats.fallback_rate)}%` : "-"} icon="help" accent="var(--gold)" />
        <StatCard label="Avg rating" value={stats?.avg_feedback != null ? stats.avg_feedback.toFixed(1) : "-"} icon="thumbs_up_down" />
        <StatCard label="Tokens" value={tokenK} icon="text_snippet" />
        <StatCard label="Latency" value={stats?.avg_latency ? `${(stats.avg_latency / 1000).toFixed(1)}s` : "-"} icon="timer" />
      </div>

      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        {issueCards.map((card) => (
          <Link key={card.key} href={card.href}>
            <Surface style={{ padding: 14 }}>
              <div className="flex items-center gap-2">
                <span className="material-symbols" style={{ fontSize: 18, color: card.accent }} aria-hidden="true">{card.icon}</span>
                <span className="text-[11px] font-medium uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>{card.label}</span>
              </div>
              <div className="mt-1 font-display text-[24px] font-semibold" style={{ color: "var(--text-primary)" }}>
                {stats?.issue_counts?.[card.key] ?? "-"}
              </div>
            </Surface>
          </Link>
        ))}
      </div>

      <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_320px]">
        <Card title="Daily volume" icon="bar_chart">
          {stats?.series ? <BarChart series={stats.series} /> : <Empty />}
        </Card>
        <RolePanel staff={staff} stats={stats} />
      </div>

      <div className="grid gap-5 lg:grid-cols-2">
        <Card title="Top gaps to curate" icon="priority_high">
          {(stats?.top_unanswered ?? []).length === 0 ? <Empty /> : (
            <ul className="divide-y" style={{ borderColor: "var(--border-light)" }}>
              {(stats?.top_unanswered ?? []).slice(0, 8).map((q, i) => (
                <li key={i} className="flex items-center gap-2 py-2">
                  <span className="flex-1 truncate text-[13px]" style={{ color: "var(--text-primary)" }}>{q.question}</span>
                  <span className="shrink-0 text-[11px]" style={{ color: "var(--text-tertiary)" }}>{q.count}x</span>
                  <Link href={`/admin/responses?question=${encodeURIComponent(q.question)}`} className="shrink-0 rounded-md px-2 py-1 text-[11px] font-semibold transition hover:opacity-90" style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}>
                    Draft
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <Card title="Recent ministry questions" icon="history">
          {queries.length === 0 ? <Empty /> : (
            <ul className="divide-y" style={{ borderColor: "var(--border-light)" }}>
              {queries.map((q, i) => (
                <li key={i} className="flex items-center gap-3 py-2">
                  <div className="min-w-0 flex-1">
                    <div className="truncate text-[13px]" style={{ color: "var(--text-primary)" }}>{q.question}</div>
                    <div className="text-[10px]" style={{ color: "var(--text-tertiary)" }}>{q.asked_at ? new Date(q.asked_at).toLocaleString() : ""}</div>
                  </div>
                  <span className="shrink-0 rounded-full px-2 py-0.5 text-[10px] font-semibold" style={q.confident ? { background: "var(--accent-light)", color: "var(--accent-text)" } : { background: "var(--gold-light)", color: "var(--gold)" }}>
                    {q.confident ? "answered" : "fallback"}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </div>
    </div>
  );
}
