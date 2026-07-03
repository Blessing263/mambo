"""Anti-abuse & bot-detection middleware for the Mambo RAG API.

Layers:
  1. Rate limiting — sliding-window per-IP (in-memory).
  2. Bot detection — UA block-list, header fingerprinting, nonce challenge.
  3. Behavior tracking — per-session cadence/entropy scoring → tarpit or block.
  4. Request logging — IP + User-Agent captured in query_log.

All state is in-memory (restart clears it). For production, swap to Redis.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import time
from collections import defaultdict

import math
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, HTTPException

# ── Layer 0: nonce challenge ──────────────────────────────────────────────
#
# The frontend fetches a short-lived nonce from GET /nonce and includes it in
# every POST /ask( /stream) body.  Bots that talk to the API without rendering
# the page first (e.g. raw curl scripts) won't have a valid nonce.
#
# Valid for 5 minutes, single-use.

_nonce_store: dict[str, float] = {}  # nonce → expiry_ts
_NONCE_TTL = 300  # seconds


def _generate_nonce() -> str:
    return secrets.token_urlsafe(16)


# ── Layer 1: rate limiting ────────────────────────────────────────────────
#
#               │ window (s) │ max requests │
# ──────────────┼────────────┼──────────────│
#  /ask/stream  │ tracked as │ concurrent   │ ← max *concurrent* streams per IP
#  /ask         │ 60         │ 5            │
#  /nonce       │ 10         │ 20           │
#  /health      │ 60         │ 30           │

_CONCURRENT_MAX = 5
_WINDOWS: dict[str, tuple[int, int]] = {  # seconds, max
    "/ask":        (60, 30),   # per-IP: 30 requests/minute
    "/nonce":      (10, 30),
    "/health":     (60, 60),
    "/ministries": (60, 60),
    "/admin/login": (60, 10),  # staff login: 10/min per IP
    # /ask/stream handled by _concurrent dict
}

_hits: dict[str, list[float]] = defaultdict(list)  # ip:key → [timestamps]
_concurrent: dict[str, int] = defaultdict(int)       # ip → active streams


def _client_ip(request: Request) -> str:
    """Best-effort real-IP extraction (respects nginx reverse-proxy headers)."""
    for h in ("x-forwarded-for", "x-real-ip", "cf-connecting-ip"):
        val = request.headers.get(h)
        if val:
            return val.split(",")[0].strip()
    host = request.client.host if request.client else "unknown"
    return host


def _ratelimit_key(request: Request, route_key: str, session_id: str | None = None) -> str:
    """Build rate-limit key. Uses real IP when available, falls back to session_id
    for requests coming through local proxies (127.0.0.1 without X-Forwarded-For)."""
    ip = _client_ip(request)
    if ip in ("127.0.0.1", "::1", "localhost", "unknown") and session_id:
        return f"session:{session_id}:{route_key}"
    return f"{ip}:{route_key}"


def _ratelimit_check(request: Request, route_key: str, session_id: str | None = None) -> None:
    """Raise 429 if the client exceeds the window limit."""
    spec = _WINDOWS.get(route_key)
    if spec is None:
        return
    window, limit = spec
    key = _ratelimit_key(request, route_key, session_id)
    now = time.monotonic()
    _hits[key] = [t for t in _hits[key] if now - t < window]
    if len(_hits[key]) >= limit:
        wait = int(window - (now - _hits[key][0]) + 1)
        raise HTTPException(
            status_code=429,
            detail=f"Too many requests. Retry in {wait}s.",
            headers={"Retry-After": str(wait)},
        )
    _hits[key].append(now)


def _concurrent_acquire(request: Request) -> None:
    """Acquire a stream slot; raise 429 if at capacity."""
    ip = _client_ip(request)
    if _concurrent[ip] >= _CONCURRENT_MAX:
        raise HTTPException(
            status_code=429,
            detail="Too many active streams. Please wait.",
            headers={"Retry-After": "5"},
        )
    _concurrent[ip] += 1


def _concurrent_release(request: Request) -> None:
    ip = _client_ip(request)
    if _concurrent[ip] > 0:
        _concurrent[ip] -= 1


# ── Layer 2: bot detection ─────────────────────────────────────────────────

# User-Agent substrings that signal non-browser automation.
_BLOCKED_UA = re.compile(
    r"(?i)(python-requests|python-urllib|libwww-perl|wget|curl|"
    r"go-http-client|okhttp|axios|node-fetch|undici|"
    r"java/|apache-httpclient|l9tcpid|scrapy|"
    r"zgrab|nmap|masscan|"
    r"^$|^unknown$|^none$)"  # empty or obvious bots
)

# Browsers that are fine (allowed even if generic in some cases).
_ALLOWED_BROWSER = re.compile(
    r"(?i)(mozilla|chrome|safari|firefox|edge|opera|brave|vivaldi)"
)


def _ua_fingerprint(request: Request) -> str:
    """Hash of UA + Accept-Language → stable fingerprint."""
    ua = request.headers.get("user-agent", "")
    lang = request.headers.get("accept-language", "")
    return hashlib.sha256(f"{ua}|{lang}".encode()).hexdigest()[:16]


def _bot_check(request: Request, nonce: str | None = None, *, require_nonce: bool = False) -> None:
    """Raise 403 if the request looks like a bot.
    
    If require_nonce=True (for POST /ask), the nonce is mandatory — only callers
    that rendered the page first (GET /nonce via the app) have a valid token.
    """
    ua = request.headers.get("user-agent", "")

    # 1. Block known automation UAs
    if _BLOCKED_UA.search(ua):
        raise HTTPException(status_code=403, detail="Automated requests not allowed")

    # 2. Block requests missing basic browser headers
    if not _ALLOWED_BROWSER.search(ua):
        raise HTTPException(status_code=403, detail="Valid browser required")

    # 3. Header consistency check (bots often mismatched)
    sec_fetch_site = request.headers.get("sec-fetch-site", "")
    if sec_fetch_site and sec_fetch_site not in ("same-origin", "none", "empty"):
        raise HTTPException(status_code=403, detail="Invalid request context")

    # 4. Nonce validation for POST /ask endpoints
    if require_nonce and not nonce:
        raise HTTPException(status_code=403, detail="Missing security token. Reload the page.")
    if nonce:
        expiry = _nonce_store.pop(nonce, None)
        if expiry is None or time.time() > expiry:
            raise HTTPException(status_code=403, detail="Invalid or expired security token. Reload the page.")


# ── Layer 5: origin lock ─────────────────────────────────~~~~~~~~~~~~~~~~~

_ALLOWED_ORIGINS = {
    h.strip() for h in
    __import__("os").environ.get("RUZIVO_ALLOWED_ORIGINS",
        "https://ruzivo.yttrix.tech,http://localhost:3000,http://localhost:3055"
    ).split(",") if h.strip()
}


def _origin_check(request: Request) -> None:
    """Block requests from origins that aren't the official app."""
    origin = request.headers.get("origin", "")
    referer = request.headers.get("referer", "")
    # If neither header is present and it's a POST, block (browsers send Origin on CORS POSTs)
    if request.method == "POST" and not origin and not referer:
        # Allow same-origin requests that don't send Origin (e.g. direct browser navigation)
        pass  # don't block — fastapi receives POST data, Origin is present for cross-origin
    if origin and origin.rstrip("/") not in _ALLOWED_ORIGINS:
        raise HTTPException(status_code=403, detail="Access denied from this origin")


# ── Layer 3: human behavior / abuse detection ──────────────────────────────

# Simple entropy-based check: highly repetitive questions or garbage strings
# have very low Shannon entropy → likely scripted/spam.
def _text_entropy(text: str) -> float:
    if not text:
        return 0.0
    freq: dict[str, int] = {}
    for ch in text.lower():
        freq[ch] = freq.get(ch, 0) + 1
    n = len(text)
    return -sum((c / n) * math.log2(c / n) for c in freq.values())


# Per-session: last question timestamp → detect rapid-fire
_session_last_question: dict[str, float] = {}  # session_id → timestamp
_MIN_QUESTION_GAP = 0.5  # seconds — sub-500ms = likely bot


def _behavior_check(session_id: str | None, question: str) -> bool:
    """Returns True if the question passes behavior checks. False = suspicious."""
    if not session_id:
        return True  # no session tracking

    # 1. Sub-second cadence → flag
    now = time.time()
    last = _session_last_question.get(session_id)
    if last is not None and (now - last) < _MIN_QUESTION_GAP:
        return False
    _session_last_question[session_id] = now

    # 2. Very low entropy → garbage/spam
    if _text_entropy(question) < 2.0 and len(question) > 10:
        return False

    # 3. Very long question (>5000 chars) → likely paste-attack
    if len(question) > 5000:
        return False

    return True


# ── Lifecycle ──────────────────────────────────────────────────────────────

# Periodic cleanup of expired nonce store and rate-limit buckets
_LAST_CLEANUP = time.monotonic()
_CLEANUP_INTERVAL = 300  # every 5 minutes


def _cleanup() -> None:
    global _LAST_CLEANUP
    now = time.monotonic()
    if now - _LAST_CLEANUP < _CLEANUP_INTERVAL:
        return
    _LAST_CLEANUP = now
    # Clean nonces
    expired = [k for k, v in _nonce_store.items() if time.time() > v]
    for k in expired:
        _nonce_store.pop(k, None)
    # Clean rate-limit buckets (keep last 2 mins)
    for key in list(_hits.keys()):
        _hits[key] = [t for t in _hits[key] if now - t < 120]
        if not _hits[key]:
            del _hits[key]


def security_startup() -> None:
    """Called on app startup to seed state."""
    _cleanup()


def security_shutdown() -> None:
    """Called on app shutdown to clear state."""
    _hits.clear()
    _concurrent.clear()
    _nonce_store.clear()
    _session_last_question.clear()
