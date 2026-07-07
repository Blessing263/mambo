/**
 * Playwright layout verification for Mambo.
 * Ensures the ChatGPT-style dual-state UI renders correctly across states,
 * themes, and viewport sizes. Run with:
 *
 *   npx playwright test --config=playwright.config.ts
 *
 * Prerequisites: the webchat dev server must be running on :3055 and the
 * RAG API on :8770 (both proxied through nginx at mambo.yttrix.tech).
 */

import { test, expect, type Page } from "@playwright/test";

const BASE = process.env.RUZIVO_TEST_URL || "http://localhost:3055";

const HERO = "What do you need to do today?";
const ASK_INPUT = "textarea[placeholder*='Ask anything']";

/** Tick the data-use consent checkbox (required before the first question). */
async function giveConsent(page: Page) {
  await page.locator("input[type='checkbox']").first().check();
}

/** Fill the ask box and submit via the Send button once it's enabled —
 *  pressing Enter early can be ignored while ministries are still loading. */
async function ask(page: Page, q: string) {
  await page.locator(ASK_INPUT).fill(q);
  const send = page.locator("button[aria-label='Send']").first();
  await expect(send).toBeEnabled();
  await send.click();
}

/** A user chat bubble containing the given text (never matches the textarea). */
function userBubble(page: Page, q: string) {
  return page.locator("main div.justify-end").filter({ hasText: q });
}

test.describe("Landing page (chat not started)", () => {
  test("Material Symbols font actually loads (regression)", async ({ page }) => {
    await page.goto(BASE);
    // The webfont must be requested and end up loaded — otherwise icons render
    // as raw text ("menu", "close", "verified") and the UI is broken.
    await page.waitForFunction(() => {
      const fonts = Array.from((document as Document & { fonts: FontFaceSet }).fonts);
      return fonts.some(
        (f) => /Material Symbols/i.test(f.family) && f.status === "loaded",
      );
    }, undefined, { timeout: 15000 });
  });

  test("icons render as visible elements (regression)", async ({ page }) => {
    await page.goto(BASE);
    // Material Symbols render as text before the font loads, and as glyphs after.
    // The key check: every visible icon has a real bounding box (not 0-width).
    await page.waitForTimeout(1000); // brief settle
    const boxes = await page.locator(".material-symbols:visible").evaluateAll((els) =>
      els.map((el) => el.getBoundingClientRect()),
    );
    expect(boxes.length).toBeGreaterThan(0);
    for (const b of boxes) {
      expect(b.width).toBeGreaterThan(0);
      expect(b.height).toBeGreaterThan(0);
    }
  });

  test("renders the hero, prompt, journeys, and consent box on desktop", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator("h1")).toContainText(HERO);
    // Prompt input is visible and auto-focused
    const input = page.locator(ASK_INPUT);
    await expect(input).toBeVisible();
    await expect(input).toBeFocused();
    // Data-use consent checkbox is present and unticked by default
    const consent = page.locator("input[type='checkbox']").first();
    await expect(consent).toBeVisible();
    await expect(consent).not.toBeChecked();
    // Journey tiles — at least 3 should be visible
    // Restrict to <main> — the sidebar also has buttons whose text may
    // match the regex, and those won't be visible on most viewports.
    const tiles = page.locator("main button").filter({ hasText: /passport|tax|birth|national ID|Exam/i });
    await expect(tiles.first()).toBeVisible();
    // Sidebar is hidden on mobile, visible on desktop
    const sidebar = page.locator("aside.sidebar");
    const viewport = page.viewportSize();
    if (viewport && viewport.width >= 1024) {
      await expect(sidebar).toBeVisible();
    }
  });

  test("renders on mobile without sidebar visible", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE);
    await expect(page.locator("h1")).toContainText(HERO);
    // Sidebar off-screen
    const sidebar = page.locator("aside.sidebar");
    await expect(sidebar).not.toBeInViewport();
  });

  test("hamburger opens sidebar on mobile", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE);
    await page.locator("button[aria-label='Toggle sidebar']").click();
    const sidebar = page.locator("aside.sidebar");
    await expect(sidebar).toBeInViewport();
    // Contains sources list
    await expect(sidebar.locator("text=Sources")).toBeVisible();
    // Close sidebar
    await page.locator("button[aria-label='Close sidebar']").click();
    await expect(sidebar).not.toBeInViewport();
  });
});

test.describe("Consent gate (DPA [Chapter 12:07])", () => {
  test("asking without consent is blocked with a nudge", async ({ page }) => {
    await page.goto(BASE);
    await ask(page, "What is the AI strategy?");
    // Still on the landing page, nudge shown, no chat started
    await expect(page.locator("role=alert").filter({ hasText: /consent/i })).toBeVisible();
    await expect(page.locator("h1")).toContainText(HERO);
  });

  test("consent persists across reloads", async ({ page }) => {
    await page.goto(BASE);
    await giveConsent(page);
    await page.reload();
    await expect(page.locator("input[type='checkbox']").first()).toBeChecked();
  });
});

test.describe("Human handover (Talk to a human)", () => {
  test("opens the ministry list and a contact card", async ({ page }) => {
    await page.goto(BASE);
    await page.locator("button[aria-label='Talk to a human']").click();
    const dialog = page.locator("[role='dialog']");
    await expect(dialog).toBeVisible();
    // Pick a ministry from the list → its verified contact card appears
    await dialog.locator("button").filter({ hasText: "Home Affairs" }).click();
    await expect(dialog.locator("text=How to reach")).toBeVisible();
    // Back returns to the list; Escape closes
    await dialog.locator("button[aria-label='Back to ministry list']").click();
    await expect(dialog.locator("button").filter({ hasText: "ZIMRA" })).toBeVisible();
    await page.keyboard.press("Escape");
    await expect(dialog).not.toBeVisible();
  });
});

test.describe("Chat flow", () => {
  test("sending a question transitions to conversation view", async ({ page }) => {
    await page.goto(BASE);
    // Land on the landing page
    await expect(page.locator("h1")).toContainText(HERO);
    // Consent, type and send
    await giveConsent(page);
    await ask(page, "What is the AI strategy?");
    // Should now be in chat mode — a user message bubble appears
    await expect(userBubble(page, "What is the AI strategy?")).toBeVisible({ timeout: 10000 });
    // Watch for streaming answer to start
    await expect(page.locator("text=Mambo").first()).toBeVisible({ timeout: 15000 });
  });

  test("New chat button returns to landing", async ({ page }) => {
    await page.goto(BASE);
    await giveConsent(page);
    await ask(page, "Hello");
    // Wait for answer to start
    await expect(page.locator("text=Mambo").first()).toBeVisible({ timeout: 15000 });
    // Click new chat
    await page.locator("button[aria-label='New chat']").click();
    await expect(page.locator("h1")).toContainText(HERO);
  });

  test("switching ministry focus mid-chat starts a fresh chat", async ({ page }) => {
    await page.goto(BASE);
    await giveConsent(page);
    await ask(page, "What is the AI strategy?");
    await expect(userBubble(page, "What is the AI strategy?")).toBeVisible({ timeout: 10000 });
    // Change the Focus to another ministry from the composer row
    await page.locator("main button").filter({ hasText: /^Health$/ }).first().click();
    // Back on a fresh landing — the old conversation is gone
    await expect(page.locator("h1")).toContainText(HERO);
    await expect(userBubble(page, "What is the AI strategy?")).not.toBeVisible();
    await expect(page.locator(ASK_INPUT)).toHaveValue("");
  });
});

test.describe("Theme toggle", () => {
  test("starts in light mode", async ({ page }) => {
    await page.goto(BASE);
    const theme = await page.locator("html").getAttribute("data-theme");
    expect(theme).toBe("light");
  });

  test("toggle switches to dark mode and back", async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto(BASE);
    // Open sidebar
    await page.locator("button[aria-label='Toggle sidebar']").click();
    await expect(page.locator("aside.sidebar")).toBeInViewport();
    // Click dark mode
    await page.locator("button").filter({ hasText: /Dark mode/i }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "dark");
    // Click light mode
    await page.locator("button").filter({ hasText: /Light mode/i }).click();
    await expect(page.locator("html")).toHaveAttribute("data-theme", "light");
  });
});

test.describe("API integration", () => {
  test("/api/health returns ok", async ({ page }) => {
    const resp = await page.request.get(`${BASE}/api/health`);
    expect(resp.status()).toBe(200);
    const body = await resp.json();
    expect(body.status).toBe("ok");
  });

  test("asking a question produces an answer with text", async ({ page }) => {
    await page.goto(BASE);
    await giveConsent(page);
    await page.locator(ASK_INPUT).fill("What is Zimbabwe's National AI Strategy?");
    await page.keyboard.press("Enter");
    // Wait for streaming answer to appear (the "Mambo" label only appears when an answer does)
    await expect(page.locator("text=Mambo").first()).toBeVisible({ timeout: 90000 });
    const answer = page.locator(".answer").first();
    await expect(answer).toBeVisible({ timeout: 60000 });
    const text = await answer.innerText();
    expect(text.length).toBeGreaterThan(50);
  });
});

test.describe("Cross-browser layout", () => {
  test("full-bleed: main content fills viewport width on wide screens", async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(BASE);
    const main = page.locator("main");
    const box = await main.boundingBox();
    expect(box).not.toBeNull();
    // Main area should span most of the viewport width (not boxed at center)
    expect(box!.width).toBeGreaterThan(1200);
  });

  test("responsible text measure in conversation", async ({ page }) => {
    await page.setViewportSize({ width: 2560, height: 1440 });
    await page.goto(BASE);
    // Consent, then send a question to enter chat
    await giveConsent(page);
    await page.locator(ASK_INPUT).fill("What is the AI strategy?");
    await page.keyboard.press("Enter");
    // Wait for the answer text block
    await expect(page.locator("text=Mambo").first()).toBeVisible({ timeout: 90000 });
    await expect(page.locator(".answer").first()).toBeVisible({ timeout: 60000 });
    // Answer text area should respect a reasonable max width for readability
    const answerBox = await page.locator(".answer").first().boundingBox();
    expect(answerBox).not.toBeNull();
    // At 2560px wide, the answer block shouldn't span the whole screen
    expect(answerBox!.width).toBeLessThan(900);
  });
});
