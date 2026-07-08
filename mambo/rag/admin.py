"""Ministry admin router — the customer-service backend.

Every protected route is scoped to the logged-in staff member's ministry
(`staff.ministry_id`). Auth is session-cookie based (rag/auth.py), distinct from
the public anti-bot layer that guards the citizen /ask endpoints.
"""

from __future__ import annotations

import json
import time
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel

from shared.db import get_conn
from shared.embeddings import embed_text
from . import auth, service
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
    same_origin(request)
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
def me(request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/me")
    return _staff_dict(staff)


# ── analytics + queries (ministry-scoped) ────────────────────────────────────
@router.get("/stats")
def stats(request: Request, days: int = 30, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/stats")
    mid = staff.ministry_id
    if not mid:
        return {"total": 0, "answered": 0, "fallback_rate": None, "avg_feedback": None,
                "token_count": 0, "avg_latency": None,
                "top_questions": [], "top_unanswered": [], "series": []}
    clamped_days = max(1, min(days, 365))
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("""SELECT count(*) AS total,
               count(*) FILTER (WHERE coalesce(evidence_status, CASE WHEN confident AND answered THEN 'answered' ELSE 'unsupported' END) = 'answered') AS answered,
               avg(feedback) FILTER (WHERE feedback IS NOT NULL) AS avg_feedback,
               coalesce(sum(token_count), 0) AS token_count,
               coalesce(round(avg(latency_ms) FILTER (WHERE latency_ms > 0)), 0) AS avg_latency
               FROM query_log WHERE %s = ANY(detected_ministries)
               AND asked_at > now() - make_interval(days => %s);""", (mid, clamped_days))
        agg = cur.fetchone()
        cur.execute("""SELECT question, count(*) AS n FROM query_log
               WHERE %s = ANY(detected_ministries)
               AND asked_at > now() - make_interval(days => %s)
               GROUP BY question ORDER BY n DESC LIMIT 10;""", (mid, clamped_days))
        top_q = cur.fetchall()
        cur.execute("""SELECT question, count(*) AS n FROM query_log
               WHERE %s = ANY(detected_ministries)
               AND asked_at > now() - make_interval(days => %s)
                 AND coalesce(evidence_status, CASE WHEN confident AND answered THEN 'answered' ELSE 'unsupported' END)
                     IN ('partial', 'unsupported', 'declined')
               GROUP BY question ORDER BY n DESC LIMIT 10;""", (mid, clamped_days))
        top_u = cur.fetchall()
        cur.execute("""SELECT date_trunc('day', asked_at) AS d, count(*) AS n FROM query_log
               WHERE %s = ANY(detected_ministries)
               AND asked_at > now() - make_interval(days => %s)
               GROUP BY d ORDER BY d;""", (mid, clamped_days))
        series = cur.fetchall()
    total, answered = agg["total"], agg["answered"]
    return {
        "total": total,
        "answered": answered,
        "fallback_rate": round((total - answered) / total, 3) if total else None,
        "avg_feedback": round(float(agg["avg_feedback"]), 2) if agg["avg_feedback"] is not None else None,
        "token_count": int(agg["token_count"]),
        "avg_latency": int(agg["avg_latency"]) if agg["avg_latency"] else None,
        "top_questions": [{"question": r["question"], "count": r["n"]} for r in top_q],
        "top_unanswered": [{"question": r["question"], "count": r["n"]} for r in top_u],
        "series": [{"day": r["d"].isoformat() if r["d"] else None, "count": r["n"]} for r in series],
    }


@router.get("/queries")
def queries(request: Request, limit: int = 50, offset: int = 0, q: str = "", staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/queries")
    mid = staff.ministry_id
    if not mid:
        return []
    with get_conn() as conn, conn.cursor() as cur:
        if q.strip():
            cur.execute(
                """SELECT asked_at, question, detected_ministries, confident, answered,
                          feedback, latency_ms
                   FROM query_log WHERE %s = ANY(detected_ministries)
                     AND question ILIKE %s
                   ORDER BY asked_at DESC LIMIT %s OFFSET %s;""",
                (mid, f"%{q.strip()}%", max(1, min(limit, 200)), max(0, offset)),
            )
        else:
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


@router.get("/questions")
def question_inbox(
    request: Request,
    limit: int = 50,
    offset: int = 0,
    q: str = "",
    status: str = "",
    staff: Staff = Depends(current_staff),
):
    _ratelimit_check(request, "/admin/questions")
    mid = staff.ministry_id
    if not mid:
        return []
    limit = max(1, min(limit, 200))
    offset = max(0, offset)
    filters = ["%s = ANY(detected_ministries)"]
    params: list = [mid]
    if q.strip():
        filters.append("question ILIKE %s")
        params.append(f"%{q.strip()}%")
    if status.strip():
        filters.append("coalesce(evidence_status, CASE WHEN confident AND answered THEN 'answered' ELSE 'unsupported' END) = %s")
        params.append(status.strip())
    params += [limit, offset]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""SELECT id, asked_at, question, detected_ministries, confident, answered,
                      coalesce(evidence_status, CASE WHEN confident AND answered THEN 'answered' ELSE 'unsupported' END) AS evidence_status,
                      reviewed, feedback, latency_ms
               FROM query_log
               WHERE {' AND '.join(filters)}
               ORDER BY asked_at DESC LIMIT %s OFFSET %s;""",
            params,
        )
        rows = cur.fetchall()
    return [
        {
            "id": str(r["id"]),
            "asked_at": r["asked_at"].isoformat() if r["asked_at"] else None,
            "question": r["question"],
            "ministries": r["detected_ministries"],
            "confident": r["confident"],
            "answered": r["answered"],
            "evidence_status": r["evidence_status"],
            "reviewed": r["reviewed"],
            "feedback": r["feedback"],
            "latency_ms": r["latency_ms"],
        }
        for r in rows
    ]


class MinistryProfileUpdate(BaseModel):
    contact: dict


@router.get("/ministry-profile")
def ministry_profile(request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/profile")
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, name, short_name, contact, domains, updated_at
               FROM ministries WHERE id = %s;""",
            (staff.ministry_id,),
        )
        ministry = cur.fetchone()
        cur.execute(
            """SELECT title, source_url, fetched_at, status
               FROM documents WHERE ministry_id = %s
               ORDER BY fetched_at DESC NULLS LAST LIMIT 25;""",
            (staff.ministry_id,),
        )
        docs = cur.fetchall()
    if not ministry:
        raise HTTPException(status_code=404, detail="Ministry not found")
    return {
        "id": ministry["id"],
        "name": ministry["name"],
        "short_name": ministry["short_name"],
        "contact": ministry["contact"],
        "domains": ministry["domains"],
        "updated_at": ministry["updated_at"].isoformat() if ministry["updated_at"] else None,
        "sources": [
            {
                "title": d["title"],
                "url": d["source_url"],
                "fetched_at": d["fetched_at"].isoformat() if d["fetched_at"] else None,
                "status": d["status"],
            }
            for d in docs
        ],
    }


@router.put("/ministry-profile")
def update_ministry_profile(body: MinistryProfileUpdate, request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/profile-mutate")
    same_origin(request)
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    allowed = {
        "phone", "whatsapp", "email", "address", "hours", "office_hours",
        "service_counter_url", "last_verified_at", "human_review_owner",
    }
    cleaned = {k: v for k, v in (body.contact or {}).items() if k in allowed}
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """UPDATE ministries SET contact = %s, updated_at = now()
               WHERE id = %s RETURNING contact, updated_at;""",
            (json.dumps(cleaned), staff.ministry_id),
        )
        row = cur.fetchone()
        conn.commit()
    return {
        "contact": row["contact"],
        "updated_at": row["updated_at"].isoformat() if row["updated_at"] else None,
    }


# ── official-response workflow (ministry-scoped) ────────────────────────────
OfficialStatus = Literal["draft", "pending_review", "approved", "archived"]


class OfficialIn(BaseModel):
    question: str
    answer: str
    citations: list[dict] | None = None
    service_area: str | None = None
    status: OfficialStatus | None = "draft"


class OfficialUpdate(BaseModel):
    question: str | None = None
    answer: str | None = None
    citations: list[dict] | None = None
    service_area: str | None = None
    enabled: bool | None = None
    change_note: str | None = None


def _response_row(cur, rid: str, ministry_id: str) -> dict | None:
    cur.execute(
        """SELECT id, ministry_id, question, question_norm, answer, citations,
                  service_area, status, enabled, valid_from, review_due_at,
                  created_by, submitted_by, approved_by, archived_by,
                  created_at, updated_at, submitted_at, approved_at, archived_at
           FROM official_responses WHERE id = %s AND ministry_id = %s;""",
        (rid, ministry_id),
    )
    return cur.fetchone()


def _official_dict(r: dict) -> dict:
    return {
        "id": str(r["id"]),
        "ministry_id": r["ministry_id"],
        "question": r["question"],
        "answer": r["answer"],
        "citations": r["citations"],
        "service_area": r["service_area"],
        "status": r["status"],
        "enabled": r["enabled"],
        "valid_from": r["valid_from"].isoformat() if r["valid_from"] else None,
        "review_due_at": r["review_due_at"].isoformat() if r["review_due_at"] else None,
        "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
        "submitted_at": r["submitted_at"].isoformat() if r["submitted_at"] else None,
        "approved_at": r["approved_at"].isoformat() if r["approved_at"] else None,
        "archived_at": r["archived_at"].isoformat() if r["archived_at"] else None,
    }


def _record_version(cur, old: dict | None, new_status: str, new_answer: str,
                    staff_id: str, note: str | None = None) -> None:
    cur.execute(
        """INSERT INTO official_response_versions
              (response_id, edited_by, old_status, new_status, old_answer, new_answer, change_note)
           VALUES (%s, %s, %s, %s, %s, %s, %s);""",
        (
            old["id"] if old else None,
            staff_id,
            old["status"] if old else None,
            new_status,
            old["answer"] if old else None,
            new_answer,
            note,
        ),
    )


def _refresh_official_chunks(cur, response: dict) -> None:
    cur.execute("DELETE FROM official_response_chunks WHERE response_id = %s;", (response["id"],))
    if response["status"] != "approved" or not response["enabled"]:
        return
    text = f"Official question: {response['question']}\n\nOfficial answer:\n{response['answer']}"
    embedding = None
    dim = None
    try:
        embedding = embed_text(text, is_query=False)
        dim = len(embedding)
    except Exception:
        # The exact-match path still works; pending chunks can be embedded later.
        pass
    cur.execute(
        """INSERT INTO official_response_chunks
              (response_id, ministry_id, chunk_index, text, embedding, dim)
           VALUES (%s, %s, 0, %s, %s, %s)
           ON CONFLICT (response_id, chunk_index)
           DO UPDATE SET text = EXCLUDED.text, embedding = EXCLUDED.embedding, dim = EXCLUDED.dim;""",
        (response["id"], response["ministry_id"], text, embedding, dim),
    )


@router.get("/official-responses")
def list_official_responses(
    request: Request,
    limit: int = 100,
    offset: int = 0,
    q: str = "",
    status: str = "",
    staff: Staff = Depends(current_staff),
):
    _ratelimit_check(request, "/admin/official-list")
    if not staff.ministry_id:
        return []
    filters = ["ministry_id = %s"]
    params: list = [staff.ministry_id]
    if q.strip():
        filters.append("(question ILIKE %s OR answer ILIKE %s OR service_area ILIKE %s)")
        like = f"%{q.strip()}%"
        params += [like, like, like]
    if status.strip():
        filters.append("status = %s")
        params.append(status.strip())
    params += [max(1, min(limit, 500)), max(0, offset)]
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            f"""SELECT * FROM official_responses
                WHERE {' AND '.join(filters)}
                ORDER BY updated_at DESC LIMIT %s OFFSET %s;""",
            params,
        )
        rows = cur.fetchall()
    return [_official_dict(r) for r in rows]


@router.post("/official-responses")
def create_official_response(body: OfficialIn, request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/official-mutate")
    same_origin(request)
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    status = body.status or "draft"
    if status == "approved" and not body.citations:
        raise HTTPException(status_code=400, detail="Approved responses need at least one citation")
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO official_responses
                  (ministry_id, question, question_norm, answer, citations,
                   service_area, status, created_by, submitted_by, approved_by,
                   submitted_at, approved_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s,
                       CASE WHEN %s IN ('pending_review','approved') THEN %s ELSE NULL END,
                       CASE WHEN %s = 'approved' THEN %s ELSE NULL END,
                       CASE WHEN %s IN ('pending_review','approved') THEN now() ELSE NULL END,
                       CASE WHEN %s = 'approved' THEN now() ELSE NULL END)
               RETURNING *;""",
            (
                staff.ministry_id, body.question, normalize_question(body.question),
                body.answer, json.dumps(body.citations or []), body.service_area,
                status, staff.id, status, staff.id, status, staff.id, status, status,
            ),
        )
        row = cur.fetchone()
        _record_version(cur, row, row["status"], row["answer"], staff.id, "Created official response")
        _refresh_official_chunks(cur, row)
        conn.commit()
    service.invalidate_reviewed_cache()
    return _official_dict(row)


@router.put("/official-responses/{rid}")
def update_official_response(rid: str, body: OfficialUpdate, request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/official-mutate")
    same_origin(request)
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    with get_conn() as conn, conn.cursor() as cur:
        old = _response_row(cur, rid, staff.ministry_id)
        if not old:
            raise HTTPException(status_code=404, detail="Not found")
        next_citations = body.citations if body.citations is not None else old["citations"]
        if old["status"] == "approved" and not next_citations:
            raise HTTPException(status_code=400, detail="Approved responses need at least one citation")
        sets, params = [], []
        if body.question is not None:
            sets += ["question = %s", "question_norm = %s"]
            params += [body.question, normalize_question(body.question)]
        if body.answer is not None:
            sets.append("answer = %s"); params.append(body.answer)
        if body.citations is not None:
            sets.append("citations = %s"); params.append(json.dumps(body.citations))
        if body.service_area is not None:
            sets.append("service_area = %s"); params.append(body.service_area)
        if body.enabled is not None:
            sets.append("enabled = %s"); params.append(body.enabled)
        if not sets:
            raise HTTPException(status_code=400, detail="No fields to update")
        sets.append("updated_at = now()")
        params += [rid, staff.ministry_id]
        cur.execute(
            f"""UPDATE official_responses SET {', '.join(sets)}
                WHERE id = %s AND ministry_id = %s RETURNING *;""",
            params,
        )
        row = cur.fetchone()
        _record_version(cur, old, row["status"], row["answer"], staff.id, body.change_note or "Updated response")
        _refresh_official_chunks(cur, row)
        conn.commit()
    service.invalidate_reviewed_cache()
    return _official_dict(row)


def _set_official_status(rid: str, status: OfficialStatus, request: Request,
                         staff: Staff, note: str = "") -> dict:
    _ratelimit_check(request, "/admin/official-mutate")
    same_origin(request)
    if not staff.ministry_id:
        raise HTTPException(status_code=403, detail="No ministry assigned")
    with get_conn() as conn, conn.cursor() as cur:
        old = _response_row(cur, rid, staff.ministry_id)
        if not old:
            raise HTTPException(status_code=404, detail="Not found")
        if status == "approved" and not old["citations"]:
            raise HTTPException(status_code=400, detail="Approved responses need at least one citation")
        if status == "pending_review":
            extra = ", submitted_by = %s, submitted_at = now()"
            actor_params = [staff.id]
        elif status == "approved":
            extra = ", approved_by = %s, approved_at = now(), submitted_at = coalesce(submitted_at, now())"
            actor_params = [staff.id]
        elif status == "archived":
            extra = ", archived_by = %s, archived_at = now()"
            actor_params = [staff.id]
        else:
            extra = ""
            actor_params = []
        cur.execute(
            f"""UPDATE official_responses
                SET status = %s, updated_at = now(){extra}
                WHERE id = %s AND ministry_id = %s RETURNING *;""",
            [status, *actor_params, rid, staff.ministry_id],
        )
        row = cur.fetchone()
        _record_version(cur, old, row["status"], row["answer"], staff.id, note or f"Status changed to {status}")
        _refresh_official_chunks(cur, row)
        conn.commit()
    service.invalidate_reviewed_cache()
    return _official_dict(row)


@router.post("/official-responses/{rid}/submit")
def submit_official_response(rid: str, request: Request, staff: Staff = Depends(current_staff)):
    return _set_official_status(rid, "pending_review", request, staff, "Submitted for review")


@router.post("/official-responses/{rid}/approve")
def approve_official_response(rid: str, request: Request, staff: Staff = Depends(current_staff)):
    return _set_official_status(rid, "approved", request, staff, "Approved for citizen answers and RAG retrieval")


@router.post("/official-responses/{rid}/archive")
def archive_official_response(rid: str, request: Request, staff: Staff = Depends(current_staff)):
    return _set_official_status(rid, "archived", request, staff, "Archived response")


@router.get("/official-responses/{rid}/versions")
def official_response_versions(rid: str, request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/official-list")
    if not staff.ministry_id:
        return []
    with get_conn() as conn, conn.cursor() as cur:
        if not _response_row(cur, rid, staff.ministry_id):
            raise HTTPException(status_code=404, detail="Not found")
        cur.execute(
            """SELECT id, edited_by, old_status, new_status, change_note, created_at
               FROM official_response_versions
               WHERE response_id = %s ORDER BY created_at DESC LIMIT 50;""",
            (rid,),
        )
        rows = cur.fetchall()
    return [
        {
            "id": str(r["id"]),
            "edited_by": str(r["edited_by"]) if r["edited_by"] else None,
            "old_status": r["old_status"],
            "new_status": r["new_status"],
            "change_note": r["change_note"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
        }
        for r in rows
    ]


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
def list_reviewed(request: Request, limit: int = 100, offset: int = 0, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/reviewed-list")
    if not staff.ministry_id:
        return []
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT id, question, answer, citations, enabled, updated_at
               FROM reviewed_answers WHERE ministry_id = %s ORDER BY updated_at DESC
               LIMIT %s OFFSET %s;""",
            (staff.ministry_id, max(1, min(limit, 500)), max(0, offset)),
        )
        rows = cur.fetchall()
    return [{"id": str(r["id"]), "question": r["question"], "answer": r["answer"],
             "citations": r["citations"], "enabled": r["enabled"],
             "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None} for r in rows]


@router.post("/reviewed")
def create_reviewed(body: ReviewedIn, request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/reviewed-mutate")
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
    service.invalidate_reviewed_cache()
    return {"id": str(r["id"]), "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None}


@router.put("/reviewed/{rid}")
def update_reviewed(rid: str, body: ReviewedUpdate, request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/reviewed-mutate")
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
    service.invalidate_reviewed_cache()
    return {"ok": True}


@router.delete("/reviewed/{rid}")
def delete_reviewed(rid: str, request: Request, staff: Staff = Depends(current_staff)):
    _ratelimit_check(request, "/admin/reviewed-mutate")
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
    service.invalidate_reviewed_cache()
    return {"ok": True}
