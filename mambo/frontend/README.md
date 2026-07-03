# Mambo — National redesign (live-demo frontend)

A reimagined, **national-grade** frontend for **Mambo** — the Government of Zimbabwe's
plain-language, citizen-facing information assistant. Built for the live pitch to the
Minister: dignified, unmistakably Zimbabwean, and dramatic on a projector.

> *Mambo* means **"knowledge"** in Shona. One assistant across every ministry; answers
> drawn **only** from official documents, with the source shown every time.

Source project: **github.com/Blessing263/ruzivo** (`webchat/` = the Next.js face,
`rag/` = the brain, `ingestion/` + `registry/` = the data pipeline). This redesign is a
drop-in re-skin of `webchat/` — same data contracts, new identity.

---

## Run it

Open **`index.html`** — that's the full app (desktop + responsive mobile, light/dark).
Open **`mobile.html`** — the same app inside an iPhone bezel for the "mobile-first" beat.

No build step, no server. Everything is plain HTML + React (via Babel-in-browser) so it
runs from a file or any static host.

### The guided click-through (for the pitch)
1. **Landing** — the crest, the serif promise, the ask box. *"This already feels real."*
2. Click **"What is the National AI Strategy?"** → a plain-language answer **streams in**,
   then **citation cards** appear (National AI Strategy · p.12). *Trust, made visible.*
3. Click **"Find the right office"** → type/pick *"I lost my national ID"* → Mambo
   **visibly reasons across ministries** and routes to **Home Affairs · Civil Registry**
   at 96% match, then drops the steps + contact into the chat. *The flagship.*
4. Toggle **light/dark** any time (top bar or sidebar).

All answers are **scripted** for a flawless demo (no live RAG backend needed). The wiring
matches the real API response shape, so swapping in the live `askStream` is a one-file change.

---

## Design system

### Identity — "coat-of-arms energy"
- **Flag palette**: green `#1F8A4C`, gold `#E8B530`, red `#C0392B`, black, warm paper.
- **The seal** — a geometric medallion (gold ring, green field, the flag's five-point
  **star**). Used as the app mark and hero crest. *Heraldic, not figurative.*
- **The 7-stripe national ribbon** (`.flag-ribbon`) — a signature hairline accent
  (green·gold·red·black·red·gold·green) on the sidebar edge, modals and mobile header.

### Type
| Role | Family | Why |
|---|---|---|
| Display / wordmark / headlines | **Spectral** (serif) | Institutional gravitas, warmth — reads like an official national publication, not a generic AI chat. |
| UI / body / chat | **Hanken Grotesk** | Clean, legible, friendly numerals. |
| Citations / metadata | **JetBrains Mono** | Documentary precision on source refs. |

### Tokens
All design tokens live in **`theme.css`** as CSS custom properties, themed per
`[data-theme]` (dark = the pitch default, light = daytime/official). Colors, radii,
spacing rhythm, shadows, motion easings, and the flag/seal motifs are all there.

### Iconography
**Material Symbols Rounded** (Google Fonts) — the **same icon system the production app
uses**. No substitutions. Loaded via `<link>` (per the original app's note about
`@import` ordering). Ministry glyphs match the registry: `satellite_alt` (ICT),
`local_hospital` (Health), `badge` (Home Affairs), `account_balance` (Finance),
`school` (Education), `receipt_long` (ZIMRA), `assignment` (ZIMSEC), `gavel` (Veritas).

### Motion
Soft, dignified — `fadeUp` / `scaleIn` entrances, a streaming caret, "searching official
documents…" typing dots, and a routing "radar" sweep. Nothing bouncy; everything respects
`prefers-reduced-motion`.

---

## File map
```
ruzivo-redesign/
├── index.html      ← the app (load order: data → emblem → answer → sidebar → chat → router → app)
├── mobile.html     ← iPhone-framed mobile showcase
├── theme.css       ← national identity tokens (light + dark)
├── data.js         ← real ministries (from registry) + scripted cited answers + routing
├── emblem.jsx      ← Seal, Mark, Wordmark, FlagRibbon, TrustPill
├── sidebar.jsx     ← masthead + ministry source list
├── answer.jsx      ← AnswerText, CitationCard, ContactCard, ConfidenceFooter, MinistryBadge
├── chat.jsx        ← Landing hero, streaming engine, thread, Composer
├── router.jsx      ← "Find the right office" modal + in-thread routing message
├── app.jsx         ← shell, top bar, theme, mount
└── ios-frame.jsx   ← device bezel (starter component) used by mobile.html
```

## How it maps back to the real `webchat/`
- Ministry data mirrors `registry/ministries.json` (ids, short names, accent colors, contacts).
- The scripted answer shape = the real `RAG → Webchat` contract:
  `{ answer, source_ministry[], citations[], confident, fallback_contact }`.
- To go live: replace the `streamText(...)` simulation in `app.jsx` with the existing
  `askStream` from `webchat/lib/api.ts`. Everything else — components, tokens, motifs —
  ports straight into the Next.js app as a new theme + component layer.

> Explore the source repo for deeper context on the RAG trust layer, the ministry
> registry and the ingestion pipeline before extending this design.
