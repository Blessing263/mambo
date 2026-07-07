"""FastAPI surface for Module 2 — the only thing the webchat talks to.

Endpoints:
  GET  /health      — liveness
  GET  /ministries  — for the webchat ministry picker
  GET  /nonce       — short-lived nonce for bot detection
  POST /ask         — full answer + citations (non-streaming)
  POST /ask/stream  — Server-Sent Events: {type:'delta'} tokens, then {type:'done'} meta

Security: rate-limited per-IP, bot-detected via UA + nonce challenge,
human-behaviour checks, concurrent stream cap, validated input sizes.
"""

from __future__ import annotations

import json
import threading
from contextlib import asynccontextmanager
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator, model_validator

from shared.db import get_conn, healthcheck
from shared.config import settings

from . import admin, llm, service, trust
from .catalog import by_id, ministries
from .sanitize import sanitize
from .security import (
    _behavior_check,
    _bot_check,
    _client_ip,
    _concurrent_acquire,
    _concurrent_release,
    _generate_nonce,
    _store_nonce,
    _origin_check,
    _ratelimit_check,
)
from .warmup import warmup_embeddings

IS_PROD = settings.is_prod
_ALLOWED_ORIGINS = settings.allowed_origins
_MAX_QUESTION_LEN = 2000
_MAX_HISTORY_TURNS = 20


@asynccontextmanager
async def lifespan(_app):
    threading.Thread(target=warmup_embeddings, daemon=True).start()
    yield
    service._EXEC.shutdown(wait=True)


app = FastAPI(
    title="Mambo RAG API",
    version="0.1.0",
    lifespan=lifespan,
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
)

app.include_router(admin.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


class Turn(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class AskRequest(BaseModel):
    question: str = Field(max_length=_MAX_QUESTION_LEN)
    history: list[Turn] = Field(default_factory=list, max_length=_MAX_HISTORY_TURNS)
    session_id: str | None = None
    ministry_filter: str | None = None
    nonce: str | None = None

    @field_validator("question")
    @classmethod
    def question_not_blank(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("question must not be empty")
        return v


# ── Health ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health(request: Request) -> dict:
    _ratelimit_check(request, "/health")
    try:
        return {"status": "ok", **healthcheck()}
    except Exception:
        # DB unreachable — report degraded rather than 500. Liveness still answers.
        return {"status": "degraded"}


# ── Ministries ─────────────────────────────────────────────────────────────

@app.get("/ministries")
def list_ministries(request: Request) -> list[dict]:
    _ratelimit_check(request, "/ministries")
    return [
        {
            "id": m["id"],
            "name": m["name"],
            "short_name": m["short_name"],
            "mandate": m["mandate"],
            "contact": m["contact"],
            "accent_color": m["accent_color"],
        }
        for m in ministries()
    ]


# ── Nonce (bot challenge) ──────────────────────────────────────────────────

@app.get("/nonce")
def nonce(request: Request) -> dict:
    _ratelimit_check(request, "/nonce")
    n = _generate_nonce()
    ttl = _store_nonce(n)
    return {"nonce": n, "expires_in": ttl}


# ── Ask (non-streaming) ────────────────────────────────────────────────────

@app.post("/ask")
def ask(req: AskRequest, request: Request) -> dict:
    _origin_check(request)
    _ratelimit_check(request, "/ask", session_id=req.session_id)
    _bot_check(request, nonce=req.nonce, require_nonce=True)
    if not _behavior_check(req.session_id, req.question):
        raise HTTPException(status_code=429, detail="Suspicious activity detected. Slow down.")

    return service.ask(
        req.question,
        history=[t.model_dump() for t in req.history],
        ministry_filter=req.ministry_filter,
        session_id=req.session_id,
        client_ip=_client_ip(request),
        user_agent=request.headers.get("user-agent", ""),
    )


# ── Ask (streaming SSE) ────────────────────────────────────────────────────

def _sse(obj: dict) -> str:
    return f"data: {json.dumps(obj)}\n\n"


@app.post("/ask/stream")
def ask_stream(req: AskRequest, request: Request) -> StreamingResponse:
    _origin_check(request)
    _ratelimit_check(request, "/ask/stream", session_id=req.session_id)
    _bot_check(request, nonce=req.nonce, require_nonce=True)
    _concurrent_acquire(request)
    if not _behavior_check(req.session_id, req.question):
        _concurrent_release(request)
        raise HTTPException(status_code=429, detail="Suspicious activity detected. Slow down.")

    history = [t.model_dump() for t in req.history]
    client_ip = _client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    def gen():
        try:
            # Immediate feedback while the question is understood + retrieved.
            yield _sse({"type": "status", "step": "intent", "text": "Understanding your question…"})
            prep = service.prepare_stream(req.question, history, req.ministry_filter)
            if "declined" in prep:
                d = prep["declined"]
                yield _sse({"type": "delta", "text": d["answer"]})
                yield _sse({
                    "type": "done",
                    "source_ministry": d.get("source_ministry", []),
                    "citations": [],
                    "confident": False,
                    "evidence_status": "declined",
                    "decline_reason": d.get("decline_reason"),
                    "fallback_contact": d.get("fallback_contact"),
                })
                service._log_stream(
                    req.question, req.session_id, d.get("source_ministry", []),
                    {"confident": False, "citations": []}, 0,
                    client_ip=client_ip, user_agent=user_agent,
                )
                return

            if "reviewed" in prep and prep["reviewed"]:
                # Curated (ministry-vetted) answer — served instantly, no LLM call.
                r = prep["reviewed"]
                yield _sse({"type": "delta", "text": r["answer"]})
                yield _sse({
                    "type": "done",
                    "source_ministry": r["source_ministry"],
                    "citations": r["citations"],
                    "confident": True,
                    "evidence_status": "answered",
                    "reviewed": True,
                    "fallback_contact": None,
                })
                service._log_stream(
                    req.question, req.session_id, r["source_ministry"],
                    {"confident": True, "citations": r["citations"]}, 0,
                    client_ip=client_ip, user_agent=user_agent,
                )
                return

            if "chatty_response" in prep:
                yield _sse({"type": "delta", "text": prep["chatty_response"]})
                yield _sse({
                    "type": "done",
                    "source_ministry": [],
                    "citations": [],
                    "confident": True,
                    "evidence_status": prep.get("evidence_status", "answered"),
                    "fallback_contact": None,
                })
                service._log_stream(
                    req.question, req.session_id, [],
                    {"confident": True, "citations": []}, 0,
                    client_ip=client_ip, user_agent=user_agent,
                )
                return

            results = prep["results"]
            answering = prep.get("detected") or service._distinct_ministries(results)

            if not prep["confident"]:
                fb = trust.fallback_response(req.question, answering)
                yield _sse({"type": "delta", "text": fb["answer"]})
                yield _sse({
                    "type": "done",
                    "source_ministry": fb["source_ministry"],
                    "citations": [],
                    "confident": False,
                    "evidence_status": "unsupported",
                    "service_journey": None,
                    "fallback_contact": fb["fallback_contact"],
                })
                service._log_stream(
                    req.question, req.session_id, fb["source_ministry"],
                    {"confident": False, "citations": []}, 0,
                    client_ip=client_ip, user_agent=user_agent,
                )
                return

            # Honest, progressive "thinking" steps (real values from prep), shown
            # before the answer streams. Best-effort: a catalog hiccup must never
            # block the answer, so the whole block is guarded.
            try:
                names = [by_id(m)["short_name"] for m in answering if by_id(m)]
                if names:
                    yield _sse({"type": "status", "step": "route",
                                "text": f"Routing to {', '.join(names)}"})
                if results:
                    yield _sse({"type": "status", "step": "search",
                                "text": f"Searching official documents · {len(results)} relevant"})
                    top = results[0]
                    loc = f", p.{top['page']}" if top.get("page") else ""
                    yield _sse({"type": "status", "step": "read",
                                "text": f"Reading {top.get('doc_title') or 'the top source'}{loc}"})
            except Exception:
                pass

            # Stream the answer live, accumulating the FULL text so the final
            # metadata (citations, safety-net contacts, log) matches what the user
            # actually received. The old buffer-then-clear logic left full_answer
            # empty, so citations fell back to top-3 and the contacts net never fired.
            parts: list[str] = []
            for token in llm.generate_stream(req.question, results, history=history,
                                              journey=prep.get("journey")):
                token = sanitize(token)
                if not token:
                    continue
                parts.append(token)
                yield _sse({"type": "delta", "text": token})
            full_answer = "".join(parts)

            # If the answer hedged, enrich with verified public context where
            # available (returns None when disabled or nothing useful is found).
            if service._answer_is_hedged(full_answer):
                yield _sse({"type": "status", "text": "checking public sources…"})
                verify = service._web_verify_if_uncertain(
                    full_answer, req.question, answering)
                if verify:
                    verify = sanitize(verify.lstrip("\n-* "))
                    yield _sse({"type": "delta", "text": verify})
                    full_answer += verify
                # else: the streamed RAG answer stands; the contacts safety-net
                # below still gives the user a real escalation path — no empty reply.

            citations = service._citations_from_answer(full_answer, results)
            status = service._evidence_status(
                confident=True, answer=full_answer, citations=citations)
            yield _sse({
                "type": "done",
                "source_ministry": service._distinct_ministries(results),
                "citations": citations,
                "confident": True,
                "evidence_status": status,
                "service_journey": (prep.get("journey") or {}).get("id"),
                "fallback_contact": service._contacts_safety_net(
                    full_answer, answering),
            })

            # Log after stream done — real citations now, not a placeholder [].
            token_count = max(1, len(full_answer) // 4)
            service._log_stream(
                req.question, req.session_id, answering,
                {"confident": True, "citations": citations}, 0,
                token_count=token_count,
                client_ip=client_ip, user_agent=user_agent,
            )

        finally:
            _concurrent_release(request)

    return StreamingResponse(gen(), media_type="text/event-stream")


# ── Feedback ───────────────────────────────────────────────────────────────

class FeedbackIn(BaseModel):
    session_id: str | None = None
    question: str | None = None
    feedback: Literal[1, -1]

    @model_validator(mode="after")
    def question_required(self):
        if not self.question or not self.question.strip():
            raise ValueError("question must not be empty")
        self.question = self.question.strip()
        return self


@app.post("/feedback")
def submit_feedback(body: FeedbackIn, request: Request):
    """Submit citizen feedback (👍/👎) on a specific query_log row.
    Matches by session_id + question text, or updates the most recent match."""
    _ratelimit_check(request, "/feedback")
    with get_conn() as conn, conn.cursor() as cur:
        if body.session_id:
            cur.execute(
                """
                WITH target AS (
                    SELECT id FROM query_log
                    WHERE session_id = %s AND question = %s AND feedback IS NULL
                    ORDER BY asked_at DESC
                    LIMIT 1
                )
                UPDATE query_log q
                SET feedback = %s
                FROM target
                WHERE q.id = target.id
                RETURNING q.id;
                """,
                (body.session_id, body.question, body.feedback),
            )
        else:
            cur.execute(
                """
                WITH target AS (
                    SELECT id FROM query_log
                    WHERE question = %s AND feedback IS NULL
                    ORDER BY asked_at DESC
                    LIMIT 1
                )
                UPDATE query_log q
                SET feedback = %s
                FROM target
                WHERE q.id = target.id
                RETURNING q.id;
                """,
                (body.question, body.feedback),
            )
        row = cur.fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=404, detail="No matching unanswered query found")
    return {"ok": True}


# ── Error handler — don't leak details ─────────────────────────────────────

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"detail": exc.detail},
        headers=exc.headers if exc.headers else {},
    )


@app.exception_handler(500)
async def internal_error_handler(request: Request, exc: Exception):
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )
