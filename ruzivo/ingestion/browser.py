"""Headless-browser fetching — simulates a real citizen's browser via Playwright.

Reaches official pages that a plain HTTP client cannot: those behind CDN
"managed challenge" interstitials (e.g. Cloudflare) or rendered client-side with
JavaScript. Still strictly scoped to the registry allow-list, and used only for
official government domains.
"""

from __future__ import annotations

import contextlib

from playwright.sync_api import sync_playwright

from .allowlist import is_allowed

UA = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

_CHALLENGE_HINTS = (
    "just a moment",
    "checking your browser",
    "verify you are human",
    "enable javascript and cookies",
)


def _looks_like_challenge(page) -> bool:
    title = (page.title() or "").lower()
    if any(h in title for h in _CHALLENGE_HINTS):
        return True
    with contextlib.suppress(Exception):
        body = (page.inner_text("body") or "").lower()[:500]
        if any(h in body for h in _CHALLENGE_HINTS):
            return True
    return False


@contextlib.contextmanager
def _context():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        ctx = browser.new_context(
            user_agent=UA,
            locale="en-US",
            timezone_id="Africa/Harare",
            viewport={"width": 1366, "height": 900},
            extra_http_headers={"Accept-Language": "en-US,en;q=0.9"},
        )
        # Hide the most obvious automation signal.
        ctx.add_init_script(
            "Object.defineProperty(navigator,'webdriver',{get:()=>undefined});"
        )
        try:
            yield ctx
        finally:
            browser.close()


def browser_fetch(
    url: str,
    *,
    settle_ms: int = 6000,
    max_challenge_waits: int = 5,
    timeout_ms: int = 60000,
) -> dict:
    """Render a page like a real browser. Returns html, final url, links, title."""
    if not is_allowed(url):
        raise ValueError(f"Off allow-list: {url}")
    with _context() as ctx:
        page = ctx.new_page()
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        page.wait_for_timeout(settle_ms)
        waits = 0
        while _looks_like_challenge(page) and waits < max_challenge_waits:
            page.wait_for_timeout(4000)
            waits += 1
        with contextlib.suppress(Exception):
            page.wait_for_load_state("networkidle", timeout=10000)
        html = page.content()
        final = page.url
        links = page.eval_on_selector_all(
            "a[href]", "els => Array.from(new Set(els.map(e => e.href)))"
        )
        title = page.title()
    return {"html": html, "url": final, "links": links, "title": title,
            "challenged": waits > 0}


def browser_get_bytes(
    url: str, *, prime_url: str | None = None, timeout_ms: int = 90000
) -> tuple[bytes, str]:
    """Download a binary (e.g. a PDF) through a real browser context.

    If prime_url is given, that page is visited first so any CDN clearance cookie
    is obtained before requesting the file (lets us pull files behind a challenge).
    """
    if not is_allowed(url):
        raise ValueError(f"Off allow-list: {url}")
    with _context() as ctx:
        if prime_url and is_allowed(prime_url):
            with contextlib.suppress(Exception):
                pg = ctx.new_page()
                pg.goto(prime_url, wait_until="domcontentloaded", timeout=timeout_ms)
                pg.wait_for_timeout(5000)
        resp = ctx.request.get(url, timeout=timeout_ms)
        body = resp.body()
        ctype = (resp.headers.get("content-type") or "").split(";")[0].strip().lower()
    return body, ctype
