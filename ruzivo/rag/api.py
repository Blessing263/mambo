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
import time
from typing import Literal

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import BaseModel, Field, field_validator

from shared.db import healthcheck

from . import llm, service, trust
from .catalog import ministries
from .security import (
    _behavior_check,
    _bot_check,
    _client_ip,
    _concurrent_acquire,
    _concurrent_release,
    _generate_nonce,
    _nonce_store,
    _NONCE_TTL,
    _origin_check,
    _ratelimit_check,
    _cleanup,
)

# Allowed origins for the app (tightened from "*")
_ALLOWED_ORIGINS = [
    h.strip() for h in
    __import__("os").environ.get("RUZIVO_ALLOWED_ORIGINS",
        "https://ruzivo.yttrix.tech,http://localhost:3000,http://localhost:3055"
    ).split(",") if h.strip()
]

IS_PROD = __import__("os").environ.get("RUZIVO_ENV", "").lower() == "production"
_MAX_QUESTION_LEN = 2000
_MAX_HISTORY_TURNS = 20

app = FastAPI(
    title="Ruzivo RAG API",
    version="0.1.0",
    docs_url=None if IS_PROD else "/docs",
    redoc_url=None if IS_PROD else "/redoc",
)

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
    _nonce_store[n] = time.time() + _NONCE_TTL
    return {"nonce": n, "expires_in": _NONCE_TTL}


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
    _bot_check(request, nonce=req.nonce, require_nonce=True)
    _concurrent_acquire(request)
    if not _behavior_check(req.session_id, req.question):
        _concurrent_release(request)
        raise HTTPException(status_code=429, detail="Suspicious activity detected. Slow down.")

    history = [t.model_dump() for t in req.history]
    prep = service.prepare_stream(req.question, history, req.ministry_filter)
    client_ip = _client_ip(request)
    user_agent = request.headers.get("user-agent", "")

    def gen():
        try:
            if "chatty_response" in prep:
                yield _sse({"type": "delta", "text": prep["chatty_response"]})
                yield _sse({
                    "type": "done",
                    "source_ministry": [],
                    "citations": [],
                    "confident": True,
                    "fallback_contact": None,
                })
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
                    "fallback_contact": fb["fallback_contact"],
                })
                return

            # Stream the answer live, accumulating the FULL text so the final
            # metadata (citations, safety-net contacts, log) matches what the user
            # actually received. The old buffer-then-clear logic left full_answer
            # empty, so citations fell back to top-3 and the contacts net never fired.
            parts: list[str] = []
            for token in llm.generate_stream(req.question, results, history=history):
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
                    verify = verify.lstrip("\n-* ")
                    for token in verify:
                        yield _sse({"type": "delta", "text": token})
                    full_answer += verify
                # else: the streamed RAG answer stands; the contacts safety-net
                # below still gives the user a real escalation path — no empty reply.

            citations = service._citations_from_answer(full_answer, results)
            yield _sse({
                "type": "done",
                "source_ministry": service._distinct_ministries(results),
                "citations": citations,
                "confident": True,
                "fallback_contact": service._contacts_safety_net(
                    full_answer, answering),
            })

            # Log after stream done — real citations now, not a placeholder [].
            service._log_stream(
                req.question, req.session_id, answering,
                {"confident": True, "citations": citations}, 0,
                client_ip=client_ip, user_agent=user_agent,
            )

        finally:
            _concurrent_release(request)

    return StreamingResponse(gen(), media_type="text/event-stream")


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
