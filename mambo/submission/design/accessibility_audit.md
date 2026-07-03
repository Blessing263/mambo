# Accessibility Self-Audit (WCAG 2.1 AA)

This is a **self-audit** of the Mambo webchat against the Track 2 / WCAG 2.1 AA
expectations. It records what is implemented and what is pending full verification
(automated tooling + assistive-tech testing).

## Implemented

- **Theme & contrast:** light/dark themes via CSS custom properties
  (`--text-primary/secondary/tertiary`, `--accent`, `--gold`, `--red`); body text
  uses the primary/secondary tokens designed for contrast. (Full ratio verification
  with an automated contrast checker is pending.)
- **Icon font robustness:** Material Symbols loaded via `<link>` in `<head>` with a
  `.material-symbols:not(.font-ready)` rule that hides codepoint text until the
  font is ready, plus a `document.fonts.ready` check (1.5s fallback) — so icons
  never render as stray text. (Regression-tested in `webchat/tests/layout.spec.ts`.)
- **Screen-reader semantics:** `aria-label` on the aside (`Ministry sources`),
  `aria-hidden` on the visual overlay, `aria-busy` on the loading ministry list,
  `aria-label`s on icon-only buttons (send, copy, feedback).
- **Keyboard:** Enter to send, Shift+Enter for newline; focus management on chat
  start; focus-visible reliance on the browser default (to verify across browsers).
- **Responsive:** mobile-first layout; sidebar collapses with an overlay on small
  screens; the prompt box and answer cards reflow. (Full 320→1920px sweep pending.)
- **Plain language:** answers are written for an ordinary person (system-prompt
  rule 4) — a cognitive-accessibility measure.

## Pending / to verify

- **Automated contrast ratios ≥ 4.5:1** for every text/icon combination in both
  themes (run axe-core / Lighthouse; fix any tokens under threshold).
- **Touch targets ≥ 44×44 CSS px** on all interactive elements (some compact
  controls, e.g. the 32–36 px send/copy buttons, need verification/enlargement).
- **Full keyboard navigation pass** (tab order, focus traps in the mobile sidebar,
  visible focus rings) across browsers.
- **Screen-reader walkthrough** with NVDA/VoiceOver on a real answer + citations +
  handoff card.
- **Reduced-motion** media query (disable the skeleton shimmer / fade-up).

## Honest note

Mambo's primary track is **Development**, not Design — but accessibility is treated
as part of a trustworthy public service (GOV.UK principle), so this audit is
included. The items above are the concrete path to a verifiable WCAG 2.1 AA claim;
the claim should not be made until the "pending" items are checked.
