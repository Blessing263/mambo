"""Smart fetch — fast HTTP first, headless browser only when needed.

Most pages come back fine over plain HTTP (with a browser UA). When a CDN serves
a challenge interstitial (Cloudflare "Just a moment…") or returns 403, we fall back
to a real headless-browser render. One call handles open *and* protected official
sites. Allow-list enforced on input and final URL.
"""

from __future__ import annotations

import httpx

from .allowlist import is_allowed
from .browser import browser_fetch
from .fetch import USER_AGENT

_CHALLENGE_HINTS = (
    "just a moment",
    "enable javascript and cookies",
    "checking your browser",
    "attention required",
    "cf-browser-verification",
)


def smart_fetch(url: str, *, timeout: float = 45.0) -> tuple[bytes, str, str]:
    """Return (content, content_type, final_url). Browser-renders if HTTP is blocked."""
    if not is_allowed(url):
        raise ValueError(f"off allow-list: {url}")

    try:
        with httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as c:
            r = c.get(url, timeout=timeout)
        final = str(r.url)
        ctype = r.headers.get("content-type", "").split(";")[0].strip().lower()
        if r.status_code == 200 and is_allowed(final):
            if "pdf" in ctype or final.lower().endswith(".pdf"):
                return r.content, ctype, final
            if "html" in ctype:
                head = r.text[:2500].lower()
                if not any(h in head for h in _CHALLENGE_HINTS):
                    return r.content, ctype, final
    except Exception:
        pass  # fall through to the browser

    res = browser_fetch(url)
    return res["html"].encode("utf-8"), "text/html", res["url"]
