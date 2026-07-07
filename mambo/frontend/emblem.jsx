/* ============================================================
   Emblem system — geometric national seal, wordmark, ribbon.
   Heraldic / geometric only (no figurative imagery).
   ============================================================ */
const { useState: _useStateEmblem } = React;

/* ============================================================
   Iconography — Phosphor Icons (premium line/fill set).
   We keep authoring with the original Material names and map
   them to Phosphor here, so call sites stay readable.
   ============================================================ */
const PH = {
  // ministries / sources
  satellite_alt: "broadcast",
  local_hospital: "first-aid-kit",
  badge: "identification-card",
  account_balance: "bank",
  school: "graduation-cap",
  receipt_long: "receipt",
  assignment: "clipboard-text",
  gavel: "gavel",
  public: "globe-hemisphere-east",
  // examples / topics
  smart_toy: "robot",
  payments: "money",
  directions_car: "car",
  shield: "shield-check",
  // routing
  account_tree: "tree-structure",
  auto_awesome: "sparkle",
  radar: "scan",
  lightbulb: "lightbulb",
  arrow_forward: "arrow-right",
  // actions / nav
  arrow_upward: "paper-plane-tilt",   // send → paper plane
  arrow_outward: "arrow-up-right",
  menu: "list",
  add: "plus",
  close: "x",
  menu_book: "book-open",
  edit_square: "note-pencil",
  open_in_new: "arrow-square-out",
  share: "share-network",
  content_copy: "copy",
  check: "check",
  check_circle: "check-circle",
  thumb_up: "thumbs-up",
  thumb_down: "thumbs-down",
  light_mode: "sun",
  dark_mode: "moon",
  info: "info",
  description: "file-text",
  // verification
  verified: "seal-check",
  verified_user: "seal-check",
  // contact rows
  call: "phone",
  chat: "whatsapp-logo",
  mail: "envelope-simple",
  location_on: "map-pin",
  schedule: "clock",
  language: "globe",
  update: "arrows-clockwise",
};

/* Icon — renders a Phosphor glyph. Authored with Material names.
   props: n (name), fill | weight, className, style. Sizing via style.fontSize. */
function Ico({ n, fill, weight, className = "", style }) {
  const name = PH[n] || n;
  const w = fill ? "ph-fill" : weight ? `ph-${weight}` : "ph";
  const cls = `${w} ph-${name}${className ? " " + className : ""}`;
  return <i className={cls} style={style} aria-hidden="true" />;
}

/* The official Coat of Arms of Zimbabwe (full crest, raster). */
function CoatOfArms({ height = 80, glow = false, style }) {
  return (
    <span style={{ position: "relative", display: "inline-flex", flexShrink: 0, ...style }}>
      <img
        src="assets/coat-of-arms.png"
        alt="Coat of Arms of Zimbabwe"
        style={{ height, width: "auto", display: "block",
          filter: "drop-shadow(0 6px 16px rgba(0,0,0,0.30))" }}
      />
      {glow && (
        <span style={{
          position: "absolute", inset: "-14% -8% -6%", zIndex: -1, borderRadius: "50%",
          background: "radial-gradient(circle, rgba(56,192,117,0.30), transparent 68%)",
          filter: "blur(14px)",
        }} />
      )}
    </span>
  );
}

/* 5-pointed star path on a 100×100 canvas (evokes the flag's star) */
const STAR_PATH =
  "M50 6 L61.8 38.2 L96 38.2 L68.1 58.6 L79.4 92 L50 71.5 L20.6 92 L31.9 58.6 L4 38.2 L38.2 38.2 Z";

/* The national seal — a medallion: gold ring, green field, centered star.
   size = diameter in px. tone: 'gold' | 'plain' */
function Seal({ size = 44, ring = true, glow = false }) {
  const s = size;
  return (
    <span
      style={{
        position: "relative", display: "inline-grid", placeItems: "center",
        width: s, height: s, flexShrink: 0,
      }}
    >
      <svg width={s} height={s} viewBox="0 0 100 100" style={{ display: "block" }} aria-hidden="true">
        <defs>
          <radialGradient id="sealField" cx="38%" cy="30%" r="80%">
            <stop offset="0%" stopColor="#2BA85F" />
            <stop offset="58%" stopColor="#1F8A4C" />
            <stop offset="100%" stopColor="#125C34" />
          </radialGradient>
          <linearGradient id="sealStar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F6D375" />
            <stop offset="100%" stopColor="#E0A92A" />
          </linearGradient>
          <linearGradient id="sealRing" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="#F2CE6A" />
            <stop offset="50%" stopColor="#C79420" />
            <stop offset="100%" stopColor="#E8B530" />
          </linearGradient>
        </defs>
        {ring && <circle cx="50" cy="50" r="49" fill="url(#sealRing)" />}
        <circle cx="50" cy="50" r={ring ? 43 : 49} fill="url(#sealField)" />
        {ring && <circle cx="50" cy="50" r="43" fill="none" stroke="rgba(0,0,0,0.18)" strokeWidth="0.8" />}
        <g transform="translate(50 50) scale(0.62) translate(-50 -50)">
          <path d={STAR_PATH} fill="url(#sealStar)" stroke="rgba(120,80,0,0.25)" strokeWidth="1" strokeLinejoin="round" />
        </g>
        {/* top sheen */}
        <ellipse cx="42" cy="28" rx="26" ry="14" fill="rgba(255,255,255,0.14)" />
      </svg>
      {glow && (
        <span style={{
          position: "absolute", inset: -10, borderRadius: "50%", zIndex: -1,
          background: "radial-gradient(circle, rgba(56,192,117,0.45), transparent 70%)",
          filter: "blur(8px)",
        }} />
      )}
    </span>
  );
}

/* Compact rounded-square app mark for tight spots (avatars, top bar) */
function Mark({ size = 30, radius = 9 }) {
  const s = size;
  return (
    <span style={{ width: s, height: s, display: "inline-grid", placeItems: "center", flexShrink: 0 }}>
      <svg width={s} height={s} viewBox="0 0 100 100" style={{ display: "block" }} aria-hidden="true">
        <defs>
          <radialGradient id="markField" cx="36%" cy="28%" r="85%">
            <stop offset="0%" stopColor="#2BA85F" />
            <stop offset="60%" stopColor="#1F8A4C" />
            <stop offset="100%" stopColor="#11542F" />
          </radialGradient>
          <linearGradient id="markStar" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#F6D375" />
            <stop offset="100%" stopColor="#E0A92A" />
          </linearGradient>
        </defs>
        <rect x="2" y="2" width="96" height="96" rx={radius * (100 / s)} fill="url(#markField)" />
        <rect x="2" y="2" width="96" height="96" rx={radius * (100 / s)} fill="none" stroke="rgba(236,192,74,0.5)" strokeWidth="2" />
        <g transform="translate(50 50) scale(0.52) translate(-50 -50)">
          <path d={STAR_PATH} fill="url(#markStar)" />
        </g>
      </svg>
    </span>
  );
}

/* Wordmark — Mambo set in the display serif with a gold full-stop */
function Wordmark({ size = 22, color }) {
  return (
    <span style={{
      fontFamily: "var(--font-display)", fontWeight: 700, fontSize: size,
      letterSpacing: "-0.01em", color: color || "var(--ink)", lineHeight: 1,
    }}>
      Mambo<span style={{ color: "var(--gold)" }}>.</span>
    </span>
  );
}

/* The 7-stripe national ribbon — horizontal hairline accent */
function FlagRibbon({ height = 4, radius = 0, style }) {
  return (
    <span className="flag-ribbon" style={{ display: "block", height, width: "100%", borderRadius: radius, ...style }} />
  );
}

/* Small "official source" trust seal pill */
function TrustPill({ children, icon = "verified" }) {
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 6,
      padding: "5px 11px 5px 8px", borderRadius: "var(--r-pill)",
      border: "1px solid var(--line)", background: "var(--gold-soft)",
      fontSize: 12, fontWeight: 500, color: "var(--ink-soft)", whiteSpace: "nowrap",
    }}>
      <Ico n={icon} fill style={{ fontSize: 15, color: "var(--gold)" }} />
      {children}
    </span>
  );
}

Object.assign(window, { Seal, Mark, Wordmark, FlagRibbon, TrustPill, STAR_PATH, Ico, CoatOfArms, PH });
