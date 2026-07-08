"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getMe, logout } from "@/lib/adminApi";
import type { Staff } from "@/lib/types";
import { FlagRibbon, Mark, Wordmark } from "@/components/Brand";

function NavLink({ href, label, icon, active }: { href: string; label: string; icon: string; active: boolean }) {
  return (
    <Link href={href} className="flex items-center gap-2 rounded-lg px-3 py-2 text-[13px] font-medium transition hover:bg-[var(--bg-hover)]"
      style={active ? { background: "var(--accent-light)", color: "var(--accent-text)" } : { color: "var(--text-secondary)" }}>
      <span className="material-symbols" aria-hidden="true" style={{ fontSize: 17 }}>{icon}</span>
      {label}
    </Link>
  );
}

const navGroups = [
  {
    label: "Work queues",
    links: [
      { href: "/admin", label: "Command centre", icon: "space_dashboard" },
      { href: "/admin/questions", label: "Issue inbox", icon: "assignment_late" },
      { href: "/admin/responses", label: "Official responses", icon: "fact_check" },
    ],
  },
  {
    label: "Operations",
    links: [
      { href: "/admin/settings", label: "Sources & handoff", icon: "source" },
      { href: "/admin/reviewed", label: "Reviewed answers", icon: "history_edu" },
    ],
  },
];

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  const [staff, setStaff] = useState<Staff | null>(null);
  const [loading, setLoading] = useState(true);
  const router = useRouter();
  const pathname = usePathname();

  useEffect(() => {
    getMe().then((s) => {
      if (!s && pathname !== "/admin/login") { router.replace("/admin/login"); return; }
      setStaff(s);
      setLoading(false);
    });
  }, [pathname, router]);

  if (loading) {
    return <div className="grid min-h-screen place-items-center"><Mark size={40} /></div>;
  }
  // The login page renders bare (no shell); unauthenticated users only reach /admin/login.
  if (pathname === "/admin/login" || !staff) {
    return <>{children}</>;
  }

  return (
    <div className="min-h-screen" style={{ background: "var(--bg-primary)", color: "var(--text-primary)" }}>
      <header className="sticky top-0 z-20 border-b" style={{ borderColor: "var(--border-primary)", background: "var(--bg-surface)" }}>
        <div className="mx-auto flex max-w-6xl items-center gap-3 px-4 py-3">
          <Mark size={28} />
          <Wordmark size={18} />
          <span className="mx-1" aria-hidden style={{ width: 2, height: 18, background: "var(--border-primary)" }} />
          <span className="font-display text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {staff.ministry_short_name ? `${staff.ministry_short_name} — Customer Service` : "Mambo Admin"}
          </span>
          <span className="ml-auto flex items-center gap-3">
            <span className="hidden text-[12px] sm:inline" style={{ color: "var(--text-tertiary)" }}>{staff.name}</span>
            <button onClick={() => { logout().catch(() => {}); router.replace("/admin/login"); }}
              className="inline-flex items-center gap-1 rounded-lg px-2.5 py-1.5 text-[12px] transition hover:bg-[var(--bg-hover)]"
              style={{ color: "var(--text-secondary)" }}>
              <span className="material-symbols" style={{ fontSize: 16 }}>logout</span>Sign out
            </button>
          </span>
        </div>
        <FlagRibbon height={2} />
      </header>
      <div className="mx-auto grid max-w-6xl gap-5 px-4 py-5 lg:grid-cols-[260px_minmax(0,1fr)]">
        <aside className="lg:sticky lg:top-[70px] lg:self-start">
          <div className="rounded-xl border p-3" style={{ borderColor: "var(--border-primary)", background: "var(--bg-surface)", boxShadow: "var(--shadow-sm)" }}>
            <div className="mb-3 rounded-lg p-3" style={{ background: "var(--bg-secondary)" }}>
              <div className="text-[11px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>Ministry scope</div>
              <div className="mt-1 font-display text-[15px] font-semibold" style={{ color: "var(--text-primary)" }}>
                {staff.ministry_short_name || "Unassigned"}
              </div>
              <div className="mt-2 flex flex-wrap items-center gap-2">
                <span className="rounded-full px-2 py-0.5 text-[10px] font-semibold capitalize" style={{ background: "var(--accent-light)", color: "var(--accent-text)" }}>
                  {staff.role}
                </span>
                <span className="text-[11px]" style={{ color: "var(--text-tertiary)" }}>{staff.email}</span>
              </div>
            </div>
            <nav className="space-y-4">
              {navGroups.map((group) => (
                <div key={group.label}>
                  <div className="mb-1 px-2 text-[10px] font-semibold uppercase tracking-wide" style={{ color: "var(--text-tertiary)" }}>
                    {group.label}
                  </div>
                  <div className="space-y-1">
                    {group.links.map((link) => (
                      <NavLink key={link.href} {...link} active={pathname === link.href} />
                    ))}
                  </div>
                </div>
              ))}
            </nav>
          </div>
        </aside>
        <main className="min-w-0">{children}</main>
      </div>
    </div>
  );
}
