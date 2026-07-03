/**
 * Playwright layout verification for Mambo.
 * Ensures the ChatGPT-style dual-state UI renders correctly across states,
 * themes, and viewport sizes. Run with:
 *
 *   npx playwright test --config=playwright.config.ts
 *
 * Prerequisites: the webchat dev server must be running on :3055 and the
 * RAG API on :8770 (both proxied through nginx at ruzivo.yttrix.tech).
 */

import { test, expect } from "@playwright/test";

const BASE = process.env.RUZIVO_TEST_URL || "http://localhost:3055";

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

  test("renders the hero, prompt, and example chips on desktop", async ({ page }) => {
    await page.goto(BASE);
    await expect(page.locator("h1")).toContainText("Ask the Government of Zimbabwe");
    // Prompt input is visible and auto-focused
    const input = page.locator("textarea[placeholder*='Ask a question']");
    await expect(input).toBeVisible();
    await expect(input).toBeFocused();
    // Quick example buttons — at least 3 tiles should be visible
    // Restrict to <main> — the sidebar also has buttons whose text may
    // match the regex, and those won't be visible on most viewports.
    const exampleChips = page.locator("main button").filter({ hasText: /import|passport|tax|AI|strategy|data protection|schools/i });
    await expect(exampleChips.first()).toBeVisible();
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
    await expect(page.locator("h1")).toContainText("Ask the Government of Zimbabwe");
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

test.describe("Chat flow", () => {
  test("sending a question transitions to conversation view", async ({ page }) => {
    await page.goto(BASE);
    // Land on the landing page
    await expect(page.locator("h1")).toContainText("Ask the Government");
    // Type and send
    await page.locator("textarea[placeholder*='Ask a question']").fill("What is the AI strategy?");
    await page.keyboard.press("Enter");
    // Should now be in chat mode — a user message bubble appears
    await expect(page.locator("text=What is the AI strategy?")).toBeVisible({ timeout: 10000 });
    // Watch for streaming answer to start
    await expect(page.locator("text=Mambo").first()).toBeVisible({ timeout: 15000 });
  });

  test("New chat button returns to landing", async ({ page }) => {
    await page.goto(BASE);
    await page.locator("textarea[placeholder*='Ask a question']").fill("Hello");
    await page.keyboard.press("Enter");
    // Wait for answer to start
    await expect(page.locator("text=Mambo").first()).toBeVisible({ timeout: 15000 });
    // Click new chat
    await page.locator("button[aria-label='New chat']").click();
    await expect(page.locator("h1")).toContainText("Ask the Government of Zimbabwe");
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
    await page.locator("textarea").fill("What is Zimbabwe's National AI Strategy?");
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
    // Send a question to enter chat
    await page.locator("textarea").fill("What is the AI strategy?");
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
