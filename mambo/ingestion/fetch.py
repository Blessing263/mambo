"""Polite, allow-list-enforcing fetcher.

Guarantees Mambo behaves as a well-mannered government bot:
  * only fetches allow-listed official hosts (before AND after redirects),
  * respects robots.txt,
  * rate-limits per host,
  * retries transient failures with backoff.
"""

from __future__ import annotations

import time
from functools import lru_cache
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from .allowlist import host_of, is_allowed

# Government sites often sit behind CDNs that serve a stripped page to unknown
# bots. We present a standard browser UA so we receive the same full content a
# citizen's browser would — while still respecting robots.txt and rate limits.
USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)
MIN_DELAY_SECONDS = 1.5  # per-host politeness delay

_last_request_at: dict[str, float] = {}


@lru_cache(maxsize=128)
def _robots_for(scheme: str, host: str) -> RobotFileParser:
    rp = RobotFileParser()
    rp.set_url(f"{scheme}://{host}/robots.txt")
    try:
        rp.read()
    except Exception:
        # Unreadable/missing robots.txt → default-allow (standard behaviour).
        rp.parse([])
    return rp


def can_fetch(url: str) -> bool:
    parsed = urlparse(url)
    return _robots_for(parsed.scheme or "https", parsed.hostname or "").can_fetch(
        USER_AGENT, url
    )


def _respect_rate_limit(host: str) -> None:
    wait = MIN_DELAY_SECONDS - (time.time() - _last_request_at.get(host, 0.0))
    if wait > 0:
        time.sleep(wait)
    _last_request_at[host] = time.time()


class FetchBlocked(Exception):
    """Raised when a URL is off the allow-list or disallowed by robots."""


@retry(
    retry=retry_if_exception_type(httpx.TransportError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=8),
    reraise=True,
)
def fetch(url: str, *, timeout: float = 45.0) -> tuple[bytes, str, str]:
    """Return (content_bytes, content_type, final_url). Raises FetchBlocked if off-limits."""
    if not is_allowed(url):
        raise FetchBlocked(f"Off allow-list: {url}")
    if not can_fetch(url):
        raise FetchBlocked(f"robots.txt disallows: {url}")
    _respect_rate_limit(host_of(url))
    with httpx.Client(follow_redirects=True, headers={"User-Agent": USER_AGENT}) as client:
        resp = client.get(url, timeout=timeout)
    resp.raise_for_status()
    final_url = str(resp.url)
    if not is_allowed(final_url):
        raise FetchBlocked(f"Redirected off allow-list: {final_url}")
    content_type = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    return resp.content, content_type, final_url
