"use client";

import { useId } from "react";

/* Mambo emblem system — geometric national seal, app mark, wordmark, ribbon.
   Ported from frontend/emblem.jsx, rebranded Mambo. Heraldic/geometric only.
   Gradient IDs are made unique per instance (useId) to avoid SVG <defs> collisions. */

const STAR_PATH =
  "M50 6 L61.8 38.2 L96 38.2 L68.1 58.6 L79.4 92 L50 71.5 L20.6 92 L31.9 58.6 L4 38.2 L38.2 38.2 Z";

export function Seal({
  size = 44, ring = true, glow = false,
}: { size?: number; ring?: boolean; glow?: boolean }) {
  const uid = useId().replace(/:/g, "");
  const field = `sf${uid}`, star = `ss${uid}`, rg = `sr${uid}`;
  return (
    <span style={{ position: "relative", display: "inline-grid", placeItems: "center", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox="0 0 100 100" style={{ display: "block" }} aria-hidden="true">
        <defs>
          <radialGradient id={field} cx="38%" cy="30%" r="80%">
            <stop offset="0%" stopColor="#2BA85F" /><stop offset="58%" stopColor="#1F8A4C" /><stop offset="100%" stopColor="#125C34" />
          </radialGradient>
          <linearGradient id={star} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F6D375" /><stop offset="100%" stopColor="#E0A92A" />
          </linearGradient>
          <linearGradient id={rg} x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#F2CE6A" /><stop offset="50%" stopColor="#C79420" /><stop offset="100%" stopColor="#E8B530" />
          </linearGradient>
        </defs>
        {ring && <circle cx="50" cy="50" r="49" fill={`url(#${rg})`} />}
        <circle cx="50" cy="50" r={ring ? 43 : 49} fill={`url(#${field})`} />
        {ring && <circle cx="50" cy="50" r="43" fill="none" stroke="rgba(0,0,0,0.18)" strokeWidth="0.8" />}
        <g transform="translate(50 50) scale(0.62) translate(-50 -50)">
          <path d={STAR_PATH} fill={`url(#${star})`} stroke="rgba(120,80,0,0.25)" strokeWidth="1" strokeLinejoin="round" />
        </g>
        <ellipse cx="42" cy="28" rx="26" ry="14" fill="rgba(255,255,255,0.14)" />
      </svg>
      {glow && (
        <span style={{ position: "absolute", inset: -10, borderRadius: "50%", zIndex: -1, background: "radial-gradient(circle, rgba(56,192,117,0.45), transparent 70%)", filter: "blur(8px)" }} />
      )}
    </span>
  );
}

export function Mark({ size = 30, radius = 9 }: { size?: number; radius?: number }) {
  const uid = useId().replace(/:/g, "");
  const field = `mf${uid}`, st = `ms${uid}`;
  return (
    <span style={{ width: size, height: size, display: "inline-grid", placeItems: "center", flexShrink: 0 }}>
      <svg width={size} height={size} viewBox="0 0 100 100" style={{ display: "block" }} aria-hidden="true">
        <defs>
          <radialGradient id={field} cx="36%" cy="28%" r="85%">
            <stop offset="0%" stopColor="#2BA85F" /><stop offset="60%" stopColor="#1F8A4C" /><stop offset="100%" stopColor="#11542F" />
          </radialGradient>
          <linearGradient id={st} x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F6D375" /><stop offset="100%" stopColor="#E0A92A" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="96" height="96" rx={(radius * 100) / size} fill={`url(#${field})`} />
        <rect x="2" y="2" width="96" height="96" rx={(radius * 100) / size} fill="none" stroke="rgba(236,192,74,0.5)" strokeWidth="2" />
        <g transform="translate(50 50) scale(0.52) translate(-50 -50)">
          <path d={STAR_PATH} fill={`url(#${st})`} />
        </g>
      </svg>
    </span>
  );
}

export function Wordmark({ size = 22, color }: { size?: number; color?: string }) {
  return (
    <span aria-label="Mambo" style={{ fontFamily: "var(--font-display)", fontWeight: 700, fontSize: size, letterSpacing: "-0.01em", color: color || "var(--text-primary)", lineHeight: 1 }}>
      Mambo<span style={{ color: "var(--gold)" }}>.</span>
    </span>
  );
}

export function FlagRibbon({ height = 4, radius = 0, style }: { height?: number; radius?: number; style?: React.CSSProperties }) {
  return <span className="flag-ribbon" style={{ display: "block", height, width: "100%", borderRadius: radius, ...style }} />;
}

export function TrustPill({ children, icon = "verified" }: { children: React.ReactNode; icon?: string }) {
  return (
    <span style={{ display: "inline-flex", alignItems: "center", gap: 6, padding: "5px 11px 5px 8px", borderRadius: "var(--r-pill)", border: "1px solid var(--border-primary)", background: "var(--gold-light)", fontSize: 12, fontWeight: 500, color: "var(--text-secondary)", whiteSpace: "nowrap" }}>
      <span className="material-symbols filled" style={{ fontSize: 15, color: "var(--gold)" }}>{icon}</span>
      {children}
    </span>
  );
}
