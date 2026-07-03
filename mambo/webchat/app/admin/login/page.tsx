"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/adminApi";
import { Seal } from "@/components/Brand";
import { PrimaryButton, Surface } from "@/components/ui";

const inputCls =
  "w-full rounded-lg border bg-transparent px-3 py-2 text-[14px] outline-none focus:border-[var(--accent)]";

export default function AdminLogin() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const router = useRouter();

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setErr("");
    const res = await login(email, password);
    if (res.ok) { router.replace("/admin"); return; }
    setErr("Invalid email or password");
    setBusy(false);
  }

  return (
    <div className="grid min-h-screen place-items-center px-4" style={{ background: "var(--bg-primary)" }}>
      <div className="w-full max-w-sm">
        <div className="mb-5 text-center">
          <div className="mb-3 flex justify-center"><Seal size={52} /></div>
          <h1 className="font-display text-[22px] font-semibold" style={{ color: "var(--text-primary)" }}>
            Ministry Staff Sign-In
          </h1>
          <p className="mt-1 text-[13px]" style={{ color: "var(--text-secondary)" }}>Mambo customer-service portal</p>
        </div>
        <Surface style={{ padding: 20 }}>
          <form onSubmit={submit} className="space-y-3">
            <label className="block">
              <span className="mb-1 block text-[12px] font-medium" style={{ color: "var(--text-secondary)" }}>Email</span>
              <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus
                className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} />
            </label>
            <label className="block">
              <span className="mb-1 block text-[12px] font-medium" style={{ color: "var(--text-secondary)" }}>Password</span>
              <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required
                className={inputCls} style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }} />
            </label>
            {err && <p className="text-[12px]" style={{ color: "var(--red)" }}>{err}</p>}
            <PrimaryButton type="submit" style={{ width: "100%" }}>
              {busy ? <span className="material-symbols animate-spin" style={{ fontSize: 18 }}>progress_activity</span> : "Sign in"}
            </PrimaryButton>
          </form>
        </Surface>
        <p className="mt-3 text-center text-[11px]" style={{ color: "var(--text-tertiary)" }}>
          Demo: <code style={{ fontFamily: "var(--font-mono, monospace)" }}>home_affairs@demo.mambo</code> · <code>mambo2026</code>
        </p>
      </div>
    </div>
  );
}
