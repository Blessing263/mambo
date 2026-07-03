"""Ministry admin router — the customer-service backend.

Every protected route is scoped to the logged-in staff member's ministry
(`staff.ministry_id`). Auth is session-cookie based (rag/auth.py), distinct from
the public anti-bot layer that guards the citizen /ask endpoints.
"""

from __future__ import annotations

import json
import time

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from shared.db import get_conn
from . import auth
from .auth import (SESSION_COOKIE, SESSION_TTL, IS_PROD, LoginIn, Staff,
                   current_staff, normalize_question, same_origin)
from .security import _ratelimit_check

router = APIRouter(prefix="/admin", tags=["admin"])


def _staff_dict(s: Staff) -> dict:
    return {"id": s.id, "email": s.email, "name": s.name, "role": s.role,
            "ministry_id": s.ministry_id, "ministry_short_name": s.ministry_short_name}


# ── auth (unauthenticated) ───────────────────────────────────────────────────
@router.post("/login")
def login(body: LoginIn, request: Request):
    _ratelimit_check(request, "/admin/login")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT s.id, s.ministry_id, s.email, s.name, s.role, s.password_hash,
                      m.short_name AS ministry_short_name
               FROM staff s LEFT JOIN ministries m ON m.id = s.ministry_id
               WHERE s.email = %s;""",
            (body.email,),
        )
        row = cur.fetchone()
    ok = bool(row) and auth.verify_password(body.password, row["password_hash"])
    if not ok:
        time.sleep(0.3)  # blunt timing attacks; generic error doesn't leak email-vs-password
        raise HTTPException(status_code=401, detail="Invalid email or password")
    token = auth.create_session(str(row["id"]))
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("UPDATE staff SET last_login_at = now() WHERE id = %s;", (row["id"],))
        conn.commit()
    resp = JSONResponse({"staff": _staff_dict(Staff(
        id=str(row["id"]), ministry_id=row["ministry_id"], email=row["email"], name=row["name"],
        role=row["role"], ministry_short_name=row["ministry_short_name"]))})
    resp.set_cookie(SESSION_COOKIE, token, httponly=True, secure=IS_PROD, samesite="lax",
                    max_age=SESSION_TTL, path="/")
    return resp


@router.post("/logout")
def logout(request: Request):
    auth.delete_session(request.cookies.get(SESSION_COOKIE))
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(SESSION_COOKIE, path="/")
    return resp


@router.get("/me")
def me(staff: Staff = Depends(current_staff)):
    return _staff_dict(staff)


# ── analytics + queries (ministry-scoped) ────────────────────────────────────
@router.get("/stats")
def stats(days: int = 30, staff: Staff = Depends(current_staff)):
    mid = staff.ministry_id
    if not mid:
        return {"total": 0, "answered": 0, "fallback_rate": None, "avg_feedback": None,
                "top_questions": [], "top_unanswered": [], "series": []}
    since = f"now() - interval '{max(1, min(days, 365))} days'"
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(f"""SELECT count(*) AS total,
               count(*) FILTER (WHERE confident AND answered) AS answered,
               avg(feedback) FILTER (WHERE feedback IS NOT NULL) AS avg_feedback
               FROM query_log WHERE %s = ANY(detected_ministries) AND asked_at > {since};""", (mid,))
        agg = cur.fetchone()
        cur.execute(f"""SELECT question, count(*) AS n FROM query_log
               WHERE %s = ANY(detected_ministries) AND asked_at > {since}
               GROUP BY question ORDER BY n DESC LIMIT 10;""", (mid,))
        top_q = cur.fetchall()
        cur.execute(f"""SELECT question, count(*) AS n FROM query_log
               WHERE %s = ANY(detected_ministries) AND asked_at > {since}
                 AND NOT (confident AND answered)
               GROUP BY question ORDER BY n DESC LIMIT 10;""", (mid,))
        top_u = cur.fetchall()
        cur.execute(f"""SELECT date_trunc('day', asked_at) AS d, count(*) AS n FROM query_log
               WHERE %s = ANY(detected_ministries) AND asked_at > {since}
               GROUP BY d ORDER BY d;""", (mid,))
        series = cur.fetchall()
    total, answered = agg["total"], agg["answered"]
    return {
        "total": total,
        "answered": answered,
        "fallback_rate": round((total - answered) / total, 3) if total else None,
        "avg_feedback": round(float(agg["avg_feedback"]), 2) if agg["avg_feedback"] is not None else None,
        "top_questions": [{"question": r["question"], "count": r["n"]} for r in top_q],
        "top_unanswered": [{"question": r["question"], "count": r["n"]} for r in top_u],
        "series": [{"day": r["d"].isoformat() if r["d"] else None, "count": r["n"]} for r in series],
    }


@router.get("/queries")
def queries(limit: int = 50, offset: int = 0, staff: Staff = Depends(current_staff)):
    mid = staff.ministry_id
    if not mid:
        return []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT asked_at, question, detected_ministries, confident, answered,
                      feedback, latency_ms
               FROM query_log WHERE %s = ANY(detected_ministries)
               ORDER BY asked_at DESC LIMIT %s OFFSET %s;""",
            (mid, max(1, min(limit, 200)), max(0, offset)),
        )
        rows = cur.fetchall()
    return [{"asked_at": r["asked_at"].isoformat() if r["asked_at"] else None,
             "question": r["question"], "confident": r["confident"], "answered": r["answered"],
             "feedback": r["feedback"], "latency_ms": r["latency_ms"],
             "ministries": r["detected_ministries"]} for r in rows]


# ── reviewed-answer curation (ministry-scoped CRUD) ──────────────────────────
class ReviewedIn(BaseModel):
    question: str
    answer: str
    citations: list[dict] | None = None


class ReviewedUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    citations: list[dict] | None = None
    enabled: bool | None = None


@router.get("/reviewed")
def list_reviewed(staff: Staff = Depends(current_staff)):
    if not staff.ministry_id:
        return []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, question, answer, citations, enabled, updated_at
               FROM reviewed_answers WHERE ministry_id = %s ORDER BY updated_at DESC;""",
            (staff.ministry_id,),
        )
        rows = cur.fetchall()
    return [{"id": str(r["id"]), "question": r["question"], "answer": r["answer"],
             "citations": r["citations"], "enabled": r["enabled"],
             "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None} for r in rows]


@router.post("/reviewed")
def create_reviewed(body: ReviewedIn, request: Request, staff: Staff = Depends(current_staff)):
    same_origin(request)
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO reviewed_answers (ministry_id, question, question_norm, answer, citations, enabled)
               VALUES (%s, %s, %s, %s, %s, true) RETURNING id, updated_at;""",
            (staff.ministry_id, body.question, normalize_question(body.question),
             body.answer, json.dumps(body.citations or [])),
        )
        r = cur.fetchone()
        conn.commit()
    return {"id": str(r["id"]), "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None}


@router.put("/reviewed/{rid}")
def update_reviewed(rid: str, body: ReviewedUpdate, request: Request, staff: Staff = Depends(current_staff)):
    same_origin(request)
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    sets, params = [], []
    if body.question is not None:
        sets += ["question = %s", "question_norm = %s"]
        params += [body.question, normalize_question(body.question)]
    if body.answer is not None:
        sets.append("answer = %s"); params.append(body.answer)
    if body.citations is not None:
        sets.append("citations = %s"); params.append(json.dumps(body.citations))
    if body.enabled is not None:
        sets.append("enabled = %s"); params.append(body.enabled)
    if not sets:
        raise HTTPException(status_code=400, detail="No fields to update")
    sets.append("updated_at = now()")
    params += [rid, staff.ministry_id]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""UPDATE reviewed_answers SET {', '.join(sets)}
               WHERE id = %s AND ministry_id = %s RETURNING id;""",
            params,
        )
        r = cur.fetchone()
        conn.commit()
    if not r:
        raise HTTPException(status_code=404, detail="Not found (or not in your ministry)")
    return {"ok": True}


@router.delete("/reviewed/{rid}")
def delete_reviewed(rid: str, request: Request, staff: Staff = Depends(current_staff)):
    same_origin(request)
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            "DELETE FROM reviewed_answers WHERE id = %s AND ministry_id = %s RETURNING id;",
            (rid, staff.ministry_id),
        )
        r = cur.fetchone()
        conn.commit()
    if not r:
        raise HTTPException(status_code=404, detail="Not found (or not in your ministry)")
    return {"ok": True}
