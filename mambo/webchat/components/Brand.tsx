"use client";

import { useId } from "react";

/* Mambo emblem system — flat civic seal, app mark, wordmark, ribbon.
   Design language: flat geometry, no gradients/gloss. The zigzag band quotes
   the chevron (dentelle) masonry course of the Great Zimbabwe walls; the gold
   five-point star sits in the field above it. Clip IDs are unique per
   instance (useId) to avoid SVG <defs> collisions. */

const STAR_PATH =
  "M50 6 L61.8 38.2 L96 38.2 L68.1 58.6 L79.4 92 L50 71.5 L20.6 92 L31.9 58.6 L4 38.2 L38.2 38.2 Z";

const FIELD_GREEN = "#17693C";
const RING_GOLD = "#D9A61E";
const STAR_GOLD = "#EEBE3B";

const CHEVRON_HI = "M2 80 L11 68 L20 80 L29 68 L38 80 L47 68 L56 80 L65 68 L74 80 L83 68 L92 80 L101 68";
const CHEVRON_LO = "M2 94 L11 82 L20 94 L29 82 L38 94 L47 82 L56 94 L65 82 L74 94 L83 82 L92 94 L101 82";

export function Seal({
  size = 44, ring = true, glow: _glow = false,
}: { size?: number; ring?: boolean; glow?: boolean }) {
  const clip = `sc${useId().replace(/:/g, "")}`;
  return (
    <span style={{ display: "inline-grid", placeItems: "center", width: size, height: size, flexShrink: 0 }}>
      <svg width={size} height={size} viewBox="0 0 100 100" style={{ display: "block" }} aria-hidden="true">
        <defs>
          <clipPath id={clip}><circle cx="50" cy="50" r="44" /></clipPath>
        </defs>
        <circle cx="50" cy="50" r="48" fill={FIELD_GREEN} />
        <g clipPath={`url(#${clip})`}>
          <path d={CHEVRON_HI} fill="none" stroke={RING_GOLD} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
          <path d={CHEVRON_LO} fill="none" stroke={RING_GOLD} strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" opacity="0.45" />
        </g>
        <g transform="translate(50 40) scale(0.34) translate(-50 -50)">
          <path d={STAR_PATH} fill={STAR_GOLD} />
        </g>
        {ring && <circle cx="50" cy="50" r="48" fill="none" stroke={RING_GOLD} strokeWidth="3" />}
      </svg>
    </span>
  );
}

export function Mark({ size = 30, radius = 9 }: { size?: number; radius?: number }) {
  const clip = `mc${useId().replace(/:/g, "")}`;
  const rx = (radius * 100) / size;
  return (
    <span style={{ width: size, height: size, display: "inline-grid", placeItems: "center", flexShrink: 0 }}>
      <svg width={size} height={size} viewBox="0 0 100 100" style={{ display: "block" }} aria-hidden="true">
        <defs>
          <clipPath id={clip}><rect x="2" y="2" width="96" height="96" rx={rx} /></clipPath>
        </defs>
        <rect x="2" y="2" width="96" height="96" rx={rx} fill={FIELD_GREEN} />
        <g clipPath={`url(#${clip})`}>
          <path d="M-2 84 L10 70 L22 84 L34 70 L46 84 L58 70 L70 84 L82 70 L94 84 L106 70" fill="none" stroke={RING_GOLD} strokeWidth="6" strokeLinecap="round" strokeLinejoin="round" />
        </g>
        <g transform="translate(50 40) scale(0.4) translate(-50 -50)">
          <path d={STAR_PATH} fill={STAR_GOLD} />
        </g>
        <rect x="2" y="2" width="96" height="96" rx={rx} fill="none" stroke="rgba(217,166,30,0.7)" strokeWidth="2.5" />
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
