"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { getMe, logout } from "@/lib/adminApi";
import type { Staff } from "@/lib/types";
import { FlagRibbon, Mark, Wordmark } from "@/components/Brand";

function NavLink({ href, label, active }: { href: string; label: string; active: boolean }) {
  return (
    <Link href={href} className="inline-flex items-center gap-1.5 rounded-lg px-3 py-2 text-[13px] font-medium transition hover:bg-[var(--bg-hover)]"
      style={active ? { background: "var(--accent-light)", color: "var(--accent-text)" } : { color: "var(--text-secondary)" }}>
      {label}
    </Link>
  );
}

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
      <nav className="mx-auto flex max-w-6xl flex-wrap gap-1 px-4 pt-4">
        <NavLink href="/admin" label="Dashboard" active={pathname === "/admin"} />
        <NavLink href="/admin/questions" label="Question inbox" active={pathname === "/admin/questions"} />
        <NavLink href="/admin/responses" label="Official responses" active={pathname === "/admin/responses"} />
        <NavLink href="/admin/settings" label="Sources & handoff" active={pathname === "/admin/settings"} />
        <NavLink href="/admin/reviewed" label="Reviewed answers" active={pathname === "/admin/reviewed"} />
      </nav>
      <main className="mx-auto max-w-6xl px-4 py-5">{children}</main>
    </div>
  );
}
