"use client";

import type { CSSProperties, ReactNode } from "react";
import type { Ministry } from "@/lib/types";

export function MaterialIcon({ n, filled, className = "", style }: {
  n: string; filled?: boolean; className?: string; style?: CSSProperties;
}) {
  return (
    <span className={`material-symbols${filled ? " filled" : ""}${className ? " " + className : ""}`} style={style} aria-hidden="true">{n}</span>
  );
}

export function Surface({ children, className = "", style }: {
  children: ReactNode; className?: string; style?: CSSProperties;
}) {
  return (
    <div className={className} style={{ background: "var(--grad-surface)", border: "1px solid var(--border-primary)", borderRadius: "var(--r-lg)", boxShadow: "var(--shadow-md)", ...style }}>{children}</div>
  );
}

export function PrimaryButton({ children, onClick, className = "", style, title, type = "button" }: {
  children: ReactNode; onClick?: () => void; className?: string; style?: CSSProperties; title?: string; type?: "button" | "submit";
}) {
  return (
    <button type={type} onClick={onClick} title={title} className={className}
      style={{ display: "inline-flex", alignItems: "center", justifyContent: "center", gap: 8, minHeight: 44, padding: "10px 18px", borderRadius: "var(--r-pill)", border: "none", background: "var(--grad-accent)", color: "#fff", fontWeight: 600, fontSize: 14, cursor: "pointer", boxShadow: "var(--shadow-sm)", transition: `transform var(--dur-fast) var(--ease), filter var(--dur-fast)`, ...style }}>
      {children}
    </button>
  );
}

export function IconButton({ children, onClick, label, className = "", style }: {
  children: ReactNode; onClick?: () => void; label: string; className?: string; style?: CSSProperties;
}) {
  return (
    <button type="button" onClick={onClick} aria-label={label} className={className}
      style={{ display: "grid", placeItems: "center", width: 36, height: 36, borderRadius: "var(--r-sm)", border: "none", background: "transparent", cursor: "pointer", color: "var(--text-tertiary)", transition: `all var(--dur-fast)`, ...style }}>
      {children}
    </button>
  );
}

export function Chip({ children, color, onClick, active, className = "", style }: {
  children: ReactNode; color?: string; onClick?: () => void; active?: boolean; className?: string; style?: CSSProperties;
}) {
  return (
    <button type="button" onClick={onClick} aria-pressed={active} className={className}
      style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "6px 12px", borderRadius: "var(--r-pill)", border: `1px solid ${active ? color || "var(--accent)" : "var(--border-primary)"}`, background: active ? `${color || "var(--accent)"}1f` : "transparent", color: "var(--text-secondary)", fontSize: 12, fontWeight: 500, cursor: "pointer", transition: `all var(--dur-fast)`, ...style }}>
      {children}
    </button>
  );
}

export function ministryColor(id: string, byId: Record<string, Ministry>): string {
  return byId[id]?.accent_color || "#64748b";
}
