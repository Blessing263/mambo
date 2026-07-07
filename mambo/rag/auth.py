"""Ministry-staff auth for the admin portal.

Session-based (opaque token in an httpOnly cookie) — revocable, simple, robust for
a single-server MVP. Distinct from rag/security.py (the public anti-bot layer):
admin routes use THIS (session cookie + same-origin check), NOT the nonce/origin-
lock/bot-check that guards the citizen /ask endpoints.
"""

from __future__ import annotations

import os
import secrets
from dataclasses import dataclass
from urllib.parse import urlparse

import bcrypt
from fastapi import HTTPException, Request
from pydantic import BaseModel, EmailStr

from shared.db import get_conn

SESSION_COOKIE = "mambo_admin"
SESSION_TTL = 12 * 3600  # 12 hours
IS_PROD = os.environ.get("RUZIVO_ENV", "").lower() == "production"


# ── password hashing (bcrypt; avoid passlib's bcrypt>=4.1 breakage) ──────────
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt(rounds=12)).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except Exception:
        return False


def normalize_question(question: str) -> str:
    """Single source of truth for reviewed-answer matching: lower/strip/collapse ws."""
    return " ".join((question or "").strip().lower().split())


class LoginIn(BaseModel):
    email: EmailStr
    password: str


@dataclass
class Staff:
    id: str
    ministry_id: str | None
    email: str
    name: str
    role: str
    ministry_short_name: str | None


# ── sessions ─────────────────────────────────────────────────────────────────
def create_session(staff_id: str) -> str:
    """Create a session row; return the opaque token (to set as a cookie)."""
    token = secrets.token_urlsafe(32)
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO staff_sessions (token, staff_id, expires_at) "
            "VALUES (%s, %s, now() + make_interval(secs => %s));",
            (token, staff_id, SESSION_TTL),
        )
        conn.commit()
    return token


def delete_session(token: str | None) -> None:
    if not token:
        return
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute("DELETE FROM staff_sessions WHERE token = %s;", (token,))
            conn.commit()
    except Exception:
        pass


def current_staff(request: Request) -> Staff:
    """FastAPI dependency: read the session cookie → return the scoped Staff, or 401."""
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT s.id, s.ministry_id, s.email, s.name, s.role,
                   m.short_name AS ministry_short_name
            FROM staff_sessions ss
            JOIN staff s ON s.id = ss.staff_id
            LEFT JOIN ministries m ON m.id = s.ministry_id
            WHERE ss.token = %s AND ss.expires_at > now()
            """,
            (token,),
        )
        row = cur.fetchone()
    if not row:
        raise HTTPException(status_code=401, detail="Session expired or invalid")
    return Staff(
        id=str(row["id"]), ministry_id=row["ministry_id"], email=row["email"],
        name=row["name"], role=row["role"], ministry_short_name=row["ministry_short_name"],
    )


def same_origin(request: Request) -> None:
    """Light CSRF defense for admin mutations: the Origin/Referer host must match the request host."""
    origin = request.headers.get("origin") or request.headers.get("referer") or ""
    host = request.headers.get("host", "").split(":", 1)[0]
    origin_host = urlparse(origin).hostname if origin else None
    if origin_host and host and origin_host != host:
        raise HTTPException(status_code=403, detail="Cross-origin request not allowed")
