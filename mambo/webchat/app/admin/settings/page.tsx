"use client";

import { useEffect, useState } from "react";
import { getMinistryProfile, updateMinistryProfile } from "@/lib/adminApi";
import type { Contact, MinistryProfile } from "@/lib/types";
import { PrimaryButton, Surface } from "@/components/ui";

const fields: { key: keyof Contact; label: string; placeholder: string }[] = [
  { key: "phone", label: "Phone", placeholder: "+263 ..." },
  { key: "whatsapp", label: "WhatsApp", placeholder: "+263 ..." },
  { key: "email", label: "Email", placeholder: "office@example.gov.zw" },
  { key: "address", label: "Address", placeholder: "Physical service address" },
  { key: "hours", label: "Office hours", placeholder: "Mon-Fri 08:00-16:30" },
  { key: "service_counter_url", label: "Service portal", placeholder: "https://..." },
  { key: "last_verified_at", label: "Last verified", placeholder: "2026-07-08" },
  { key: "human_review_owner", label: "Review owner", placeholder: "Unit or officer responsible" },
];

export default function SettingsPage() {
  const [profile, setProfile] = useState<MinistryProfile | null>(null);
  const [contact, setContact] = useState<Contact>({});
  const [saved, setSaved] = useState("");

  useEffect(() => {
    getMinistryProfile().then((p) => {
      setProfile(p);
      setContact(p.contact || {});
    }).catch(() => {});
  }, []);

  async function save() {
    const res = await updateMinistryProfile(contact);
    setContact(res.contact);
    setSaved("Saved");
    window.setTimeout(() => setSaved(""), 2000);
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="font-display text-[20px] font-semibold" style={{ color: "var(--text-primary)" }}>Sources & handoff</h1>
        <p className="mt-1 text-[12px]" style={{ color: "var(--text-tertiary)" }}>
          Maintain the contact details Mambo gives citizens when a human handoff is needed.
        </p>
      </div>

      <div className="grid gap-4 lg:grid-cols-[420px_minmax(0,1fr)]">
        <Surface style={{ padding: 16 }}>
          <h2 className="font-display text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>
            {profile?.short_name || "Ministry"} handoff details
          </h2>
          <div className="mt-3 space-y-3">
            {fields.map((f) => (
              <label key={f.key} className="block">
                <span className="mb-1 block text-[11px] font-medium" style={{ color: "var(--text-tertiary)" }}>{f.label}</span>
                <input
                  value={(contact[f.key] as string) || ""}
                  onChange={(e) => setContact({ ...contact, [f.key]: e.target.value })}
                  placeholder={f.placeholder}
                  className="w-full rounded-lg border bg-transparent px-3 py-2 text-[13px] outline-none focus:border-[var(--accent)]"
                  style={{ borderColor: "var(--border-primary)", color: "var(--text-primary)" }}
                />
              </label>
            ))}
            <div className="flex items-center gap-3">
              <PrimaryButton onClick={save}>Save details</PrimaryButton>
              {saved && <span className="text-[12px]" style={{ color: "var(--accent)" }}>{saved}</span>}
            </div>
          </div>
        </Surface>

        <Surface style={{ padding: 16 }}>
          <h2 className="font-display text-[16px] font-semibold" style={{ color: "var(--text-primary)" }}>Recent official sources</h2>
          {profile?.domains?.length ? (
            <p className="mt-1 text-[11px]" style={{ color: "var(--text-tertiary)" }}>
              Allowed domains: {profile.domains.join(", ")}
            </p>
          ) : null}
          {!profile?.sources?.length ? (
            <p className="py-6 text-center text-[13px]" style={{ color: "var(--text-tertiary)" }}>No sources loaded for this ministry yet.</p>
          ) : (
            <ul className="mt-3 divide-y" style={{ borderColor: "var(--border-light)" }}>
              {profile.sources.map((s, i) => (
                <li key={`${s.url}-${i}`} className="py-3">
                  <a href={s.url} target="_blank" rel="noreferrer" className="text-[13px] font-medium hover:underline" style={{ color: "var(--text-primary)" }}>
                    {s.title}
                  </a>
                  <div className="mt-0.5 flex flex-wrap gap-2 text-[10px]" style={{ color: "var(--text-tertiary)" }}>
                    <span>{s.status}</span>
                    <span>{s.fetched_at ? new Date(s.fetched_at).toLocaleDateString() : "not fetched"}</span>
                  </div>
                </li>
              ))}
            </ul>
          )}
        </Surface>
      </div>
    </div>
  );
}
