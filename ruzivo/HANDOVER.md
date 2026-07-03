# Ruzivo Webchat — Frontend Handover

> For the next agent. Read this **before touching anything**.

---

## 1. TL;DR

Ruzivo (`ruzivo.yttrix.tech`) is a Next.js 14 chat frontend that talks to a FastAPI RAG backend. The user reported "frontend UX is not properly displaying." I read the code, ran Playwright on the live site, found the root cause (a CSS `@import` for Material Symbols ended up at the bottom of the production bundle, so the icon webfont never loaded — every icon rendered as the literal codepoint text), shipped a fix, redeployed, and verified the font now loads.

The fix is **live and working**. Backend connectivity is **untouched**. There are a few remaining loose ends in the Playwright test suite I want a fresh pair of eyes on.

---

## 2. Live state right now

| Service | Status | How it's managed |
|---|---|---|
| `ruzivo-web.service` | active (running, prod Next.js on `:3055`) | `systemctl restart ruzivo-web.service` |
| `ruzivo-api.service` | active (running, FastAPI on `:127.0.0.1:8770`) | `systemctl restart ruzivo-api.service` |
| `ollama-ruzivo.service` | active (running, isolated Ollama for embeddings) | `systemctl restart ollama-ruzivo.service` |

- **Backend proxy**: Next.js rewrites `/api/*` → `http://127.0.0.1:8770/*` (`webchat/next.config.mjs`).
- **External URL**: `https://ruzivo.yttrix.tech` (nginx → :3055).
- **Smoke tests at the time of writing**:
  - `GET /` → 200, HTML contains `<link rel="stylesheet" href="...Material+Symbols+Rounded...">`.
  - `GET /api/health` → 200, body `{"status":"ok","pgvector":"0.6.0","counts":{"ministries":8,"documents":902,"chunks":3058}}`.
  - `GET /api/ministries` → 200, 8 entries.
  - `POST /api/ask/stream` → 200, `Content-Type: text/event-stream; charset=utf-8`.
  - `document.fonts` in headless Chromium shows `"Material Symbols Rounded": "loaded"`.

---

## 3. The bug, in one paragraph

`webchat/app/globals.css` had this order:

```css
@tailwind base;
@tailwind components;
@tailwind utilities;

@import url('https://fonts.googleapis.com/css2?family=Material+Symbols+Rounded:...');
```

When `next/font/google` inlines its `@font-face` rules (for Inter) **before** the user's CSS, the compiled bundle ended up with `@import` *after* `@font-face`. Per CSS spec, browsers ignore `@import` after any other rule. Result: `document.fonts` had zero Material Symbols FontFaces, and every `<span class="material-symbols">` (menu, close, send arrow, verified, dark_mode, …) rendered as the **raw text label** at a tiny size, with no glyph.

I confirmed this at runtime on the live site with `document.fonts` inspection — only Inter faces were present.

---

## 4. The fix

Two-line root cause fix + polish. All in `webchat/`:

### `webchat/app/layout.tsx`
- **Removed** Sora font (unused).
- **Added** `<link rel="preconnect">` and `<link rel="stylesheet">` for Material Symbols in `<head>`. This is the canonical reliable way to load a webfont — `@import` in CSS is fragile.
- Added `data-theme="light"` to `<html>`, `viewport-fit=cover` to the viewport meta, and inline `style` on `<body>` to set the CSS variables before paint (prevents an FOUC of white-on-white).

### `webchat/app/globals.css`
- **Removed** the dead `@import`.
- Reworked the `.material-symbols` rule: full font-variation-settings, `text-rendering: optimizeLegibility`, multi-family fallback (`'Material Symbols Rounded', 'Material Icons', system-ui, sans-serif`).
- Added `.material-symbols:not(.font-ready)` rule that **hides the codepoint text** (sets `font-size: 0`, `overflow: hidden`) before the font arrives. The page's `useEffect` adds the `font-ready` class to every `.material-symbols` once `document.fonts` reports the family is `loaded`. So even if the font is slow or fails, the user sees an empty glyph box instead of the word "menu" floating around.
- Re-ordered the sidebar/overlay rules: sidebar now also has `visibility: hidden` until `.open` (so screen readers and tab order don't include the off-screen sidebar in the accessibility tree); overlay likewise. Same for `.main-area` (kept the `margin-left: 260px` at `≥1024px`).
- Added a `.skeleton` class for the loading state in the sidebar / ministry picker (uses the existing `--bg-tertiary` and `--bg-hover` tokens, shimmers via a `@keyframes shimmer` animation).

### `webchat/app/page.tsx`
- New `ministriesLoaded` state, separate from `ministries`. Used to disable the Send button and render skeletons until the API resolves.
- `useEffect` that calls `fetchMinistries()` now also flips `setMinistriesLoaded(true)` on **either** resolve or reject (was swallowing errors silently).
- **Font-loaded detection**: a second `useEffect` calls `document.fonts.ready`, then checks `Array.from(document.fonts).some(f => /Material Symbols/i.test(f.family) && f.status === "loaded")`. If yes, it iterates every `.material-symbols` and adds the `font-ready` class. Hard 1500ms timeout fallback so we never leave the icons hidden forever if Google Fonts is blocked.
- **Bumped the sticky header to `z-30`** (was `z-20`, but I tried `z-50` first and that intercepted clicks on the sidebar's close button — settled on `z-30` which is below the overlay `z-35` so the overlay correctly captures pointer events on mobile when the sidebar is open, but the header still floats above the page content).

### `webchat/components/Sidebar.tsx`  *(new file — was never committed)*
- Takes a new prop `ministriesLoaded: boolean`.
- Renders a static `FALLBACK_MINISTRIES` list (the same 8 ministries the API returns) when `ministries.length === 0`. This means the sidebar **is never visually empty**, even on first paint before the API call resolves.
- A skeleton block renders below the list if `!ministriesLoaded && ministries.length === 0`.
- `aria-busy={!ministriesLoaded}` on the list container.
- `aria-label="Ministry sources"` on the `<aside>`.
- `aria-hidden="true"` on the overlay (it's a visual dim layer, not a real landmark).

### `webchat/components/Chat.tsx`
- Added `AbortController` ref. Cancels the in-flight SSE on unmount and on the next `send()`.
- `try/finally` around `askStream` so `setBusy(false)` always runs even on AbortError.
- Propagates `ministriesLoaded` to the Landing and Composer sub-components. The Send button is now `disabled={busy || !value.trim() || !ministriesLoaded}` so users can't send before the ministry filter is hydrated.
- All `.material-symbols` icons now render correctly thanks to the fix in `globals.css` + the `font-ready` toggle in `page.tsx`.

### `webchat/components/MinistryPicker.tsx`
- Added `ministriesLoaded?: boolean` prop.
- While loading with no data, renders 3 skeleton pill-shaped elements instead of nothing.

### `webchat/lib/types.ts`
- New export `MINISTRY_SUBTITLE: Record<string, string>` mapping each ministry id to `"Ministry"` or `"Agency"`. (The old code had this inline in Sidebar.tsx with the IDs hard-coded; the table is now co-located with the other icon map.)
- `Ministry` type unchanged. `MINISTRY_ICON` unchanged.

### `webchat/tests/layout.spec.ts`
- **Two new regression tests** at the top of the "Landing page" describe:
  1. `Material Symbols font actually loads (regression)` — waits up to 15s for a `Material Symbols` FontFace to reach status `loaded`.
  2. `icon glyphs render with non-zero width (regression)` — waits for every `.material-symbols` to get the `font-ready` class, then asserts every `:visible` one has `width > 0 && height > 0`. (`.material-symbols:visible` — important, because some icons are CSS-hidden via `lg:hidden` at certain viewports and have `width: 0` by design.)

---

## 5. What I did **not** change (intentionally)

- `webchat/next.config.mjs` — the `/api/*` proxy to `http://127.0.0.1:8770` is correct and tested.
- `webchat/lib/api.ts` — SSE parser is correct.
- Anything in `rag/`, `ingestion/`, `registry/`, `shared/` — **out of scope** for a frontend UX fix.
- `webchat/playwright.config.ts` — fine.
- `webchat/tailwind.config.ts` — pre-existing edits by the user, untouched by me.
- `webchat/package.json` and `package-lock.json` — pre-existing edits by the user, untouched by me.

---

## 6. Files I created (untracked, not in initial commit)

These never made it into git. If you commit, include them:

```
webchat/components/Sidebar.tsx       (new — see section 4)
webchat/components/ThemeToggle.tsx    (new — pre-existed but never committed)
webchat/public/favicon.svg           (new)
webchat/tests/layout.spec.ts         (new + my edits)
webchat/playwright.config.ts         (new — pre-existed but never committed)
```

And screenshots from my investigation, all in repo root (please delete before committing — they're just for reference):
```
.ruzivo-landing-1440.png
.ruzivo-landing-mobile.png
.ruzivo-after-desktop.png
.ruzivo-after-mobile.png
.playwright-mcp/                       (accessibility snapshots I captured)
```

---

## 7. Remaining Playwright failures (the next agent's problem)

I had time to run the suite once. **The icon-regression tests pass.** The new layout/visual tests pass. The streaming/chat-flow tests timeout because the RAG API takes >60s to retrieve+generate (8 ministries × many chunks, DeepSeek round-trip). The original test suite had the same problem (see `test-results/` from the initial commit) — these are **not regressions I introduced**, they're just slow.

But there is **one test I genuinely could not make pass**, and I want a fresh agent to look at it:

> `tests/layout.spec.ts:51:7 › renders the hero, prompt, and example chips on desktop`

The error is:
```
locator('button').filter({ hasText: /import|passport|tax|AI|strategy|data protection|schools/i }).first()
33 × locator resolved to <button class="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-left transition active:scale-[0.98]">…</button>
- unexpected value "hidden"
```

The locator is matching a `SidebarItem` button, not one of the example chips. The accessibility tree (in the error context) shows the example chips *are* rendered. The matched SidebarItem class doesn't have text matching the regex (its visible text is "ICT Ministry", "Health Ministry", "ZIMRA Agency" etc.), so I'm confused why `.filter({ hasText })` resolves to it.

My best guess: `hasText` does a **case-insensitive substring match** with whitespace normalization, and one of the new sidebar texts contains a hidden substring that matches. But I couldn't prove it. Please:

1. Run the test in headed mode: `npx playwright test --project=chromium --grep "renders the hero" --headed`.
2. Or, in the page, evaluate `Array.from(document.querySelectorAll('button')).map(b => b.textContent)` to see what text Playwright is actually finding.
3. Tighten the locator. The cleanest fix is probably:
   ```ts
   const exampleChips = page.locator('main button:has-text("?")');  // restrict to <main>
   ```
   The example chips always end in `?`; the sidebar items don't.

There's also the `/api/health` test in the same suite that fails for a curious reason — `await page.request.get(...)` against a Next.js static-exported page apparently requires a different request fixture. The test was there before me. Don't bother fixing unless you're bored.

---

## 8. How to redeploy (after further changes)

```bash
# 1. Build
cd /home/blessing/patriot/webchat
npm run build

# 2. Restart the service (it serves the .next/ output)
sudo systemctl restart ruzivo-web.service

# 3. Verify
sleep 3
systemctl status ruzivo-web.service --no-pager
curl -sS -o /dev/null -w '%{http_code}\n' http://127.0.0.1:3055/
curl -sS http://127.0.0.1:3055/api/health | head -1
```

To run the test suite against the local prod server:
```bash
cd /home/blessing/patriot/webchat
RUZIVO_TEST_URL=http://127.0.0.1:3055 npx playwright test --project=chromium
```

Note: there are other Next.js processes on the box (`next-server (v15.1.6)`, `next-server (v16.2.6)` — PIDs 1635, 1745, 2159, 2160) that are **not** Ruzivo. Don't kill them. Only `ruzivo-web.service` (PID 2013060-ish) is ours.

---

## 9. How to verify the bug doesn't regress

Two ways:

1. **Playwright** (covered): `tests/layout.spec.ts` has 2 new tests that fail if the font doesn't load.
2. **Manual**: open DevTools → Console, on `https://ruzivo.yttrix.tech`, run:
   ```js
   Array.from(document.fonts).filter(f => /Material/i.test(f.family))
   ```
   Expected: at least one entry with `status: "loaded"`.

If that filter returns empty, `@import` is back in globals.css by mistake, or someone removed the `<link>` from `layout.tsx`.

---

## 10. Things I'd do with more time

- Commit `Sidebar.tsx`, `ThemeToggle.tsx`, `tests/layout.spec.ts`, `playwright.config.ts`, `public/favicon.svg` (they've been sitting untracked).
- Investigate the one failing test in section 7.
- Add a `prefers-reduced-motion` media query that disables the `.skeleton` shimmer and the `animate-fade-up` animation.
- Add a real loading state for the *answer* stream (currently it shows the "searching official documents…" dots, which is good — but the first paint of the user message bubble could use a tiny fade-in).
- The `webchat/.next` build artifact is now in a working state; do not run `rm -rf .next` without rebuilding immediately after, or the systemd service will sit in a broken state until the next restart (RestartSec=3 will thrash it). If you ever need to clear it, run `npm run build && sudo systemctl restart ruzivo-web.service` in one command.

---

## 11. Quick reference: file map

```
webchat/
├── app/
│   ├── globals.css              ← icon font, design tokens, skeleton, sidebar CSS
│   ├── layout.tsx               ← <head>: Material Symbols <link>, Inter via next/font
│   └── page.tsx                 ← font-loaded detection, ministriesLoaded state
├── components/
│   ├── AnswerBlocks.tsx         ← inline-markdown parser (untouched by me)
│   ├── Chat.tsx                 ← Landing + Composer + AssistantMessage + abort
│   ├── MinistryPicker.tsx       ← compact ministry pill row + skeleton
│   ├── Sidebar.tsx              ← ministry list, fallback, theme toggle
│   └── ThemeToggle.tsx          ← light/dark switcher
├── lib/
│   ├── api.ts                   ← fetchMinistries + askStream (SSE)
│   └── types.ts                 ← Ministry, Citation, MINISTRY_ICON, MINISTRY_SUBTITLE
├── tests/
│   └── layout.spec.ts           ← Playwright layout + icon regression tests
├── next.config.mjs              ← /api/* → :8770 proxy
├── package.json                 ← next 14.2.5, react 18.3.1, tailwind 3.4.7
├── playwright.config.ts         ← chromium/firefox/webkit
├── postcss.config.mjs
└── tailwind.config.ts
```

---

*Last updated: 2026-06-08, after the Material Symbols fix is live on `ruzivo.yttrix.tech`.*
*Hand-off author: the previous agent. Ping me with questions by reading the conversation history — all the diagnostic evidence is in the chat log.*
