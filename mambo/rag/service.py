"""Orchestration: guard → route → retrieve → (confident?) → generate or fall back.
Also logs every question for analytics ("what citizens ask most"). Public
questions only; no private data.
"""

from __future__ import annotations

import json
import re
import time
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from shared.db import get_conn

from . import guard, journeys, llm, retrieval, router, trust

# Classify intent in parallel with retrieval so a real question doesn't pay
# classify latency on top of retrieval latency. Bounded pool; classify (an LLM
# call, no DB) is the only task submitted here.
_EXEC = ThreadPoolExecutor(max_workers=4)

_CITE_RE = re.compile(r"\[(\d+)\]")
K = 6

# Phrases that signal the answer is incomplete — when present, surface contacts
_HEDGE = re.compile(
    r"(does not|do not|not clear|no details|not covered|not provide|"
    r"cannot find|unable to|I recommend|I suggest|I can guide|"
    r"not have that|no procedure|no fee|"
    r"current sources do|not in the documents|"
    r"not.*(cover|explain|provide|contain|include|give|mention|"
    r"describe|state|specify))",
    re.IGNORECASE,
)

# Evidence-status badge vocabulary surfaced to the UI on every answer.
#   answered    — grounded in the official corpus, with citations
#   partial     — answered, but hedging or no citations attached
#   unsupported — retrieval too weak; fell back to ministry contacts
#   declined    — out of scope / unsafe (abstention)


def _answer_is_hedged(answer: str) -> bool:
    """Fast check: does the answer contain hedging/uncertainty language?"""
    return bool(_HEDGE.search(answer))


def _evidence_status(*, confident: bool, answer: str = "",
                     citations: list | None = None, declined: bool = False) -> str:
    if declined:
        return "declined"
    if not confident:
        return "unsupported"
    if _answer_is_hedged(answer) or not citations:
        return "partial"
    return "answered"


def _contacts_safety_net(answer: str, ministry_ids: list[str]) -> list[dict] | None:
    """If the answer signals uncertainty, return ministry contacts as a safety net."""
    if _HEDGE.search(answer):
        return trust._contacts(ministry_ids)
    return None


def _web_verify_if_uncertain(answer: str, question: str,
                              ministry_ids: list[str]) -> str | None:
    """Run web search if the answer is hedging — enriches with live results."""
    if not _HEDGE.search(answer):
        return None
    try:
        from rag.verify import verify_enrich  # noqa: PLC0415
        return verify_enrich(question, ministry_ids=ministry_ids)
    except Exception:
        return None


def _distinct_ministries(results: list[dict]) -> list[str]:
    seen: list[str] = []
    for r in results:
        if r["ministry_id"] not in seen:
            seen.append(r["ministry_id"])
    return seen


def _citations_from_answer(answer: str, contexts: list[dict]) -> list[dict]:
    indices = sorted({int(n) for n in _CITE_RE.findall(answer)})
    cites = [trust.cite(contexts[i - 1]) for i in indices if 1 <= i <= len(contexts)]
    if not cites:
        cites = trust.top_citations(contexts)
    # Deduplicate citations. A citation is a duplicate if EITHER:
    # - same URL (ignoring http/https scheme)
    # - same title (different URLs but same document name)
    seen_urls: set[str] = set()
    seen_titles: set[str] = set()
    unique: list[dict] = []
    for c in cites:
        url = re.sub(r'^https?://', '', c.get('url') or '').split('#')[0].rstrip('/')
        title_key = (c.get('title') or '').lower().strip()
        if url in seen_urls or title_key in seen_titles:
            continue
        seen_urls.add(url)
        if title_key:
            seen_titles.add(title_key)
        unique.append(c)
    return unique


def _log(question, session_id, detected, resp, latency_ms,
         client_ip: str = "", user_agent: str = "") -> None:
    try:
        with get_conn() as conn, conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO query_log
                    (session_id, question, detected_ministries, confident,
                     answered, citations, latency_ms, client_ip, user_agent)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    session_id, question, detected, resp["confident"],
                    resp["confident"], json.dumps(resp["citations"]), latency_ms,
                    client_ip[:45] if client_ip else None,
                    user_agent[:500] if user_agent else None,
                ),
            )
            conn.commit()
    except Exception:
        pass  # logging must never break answering


def _log_stream(question, session_id, detected, resp, latency_ms,
                client_ip: str = "", user_agent: str = "") -> None:
    _log(question, session_id, detected, resp, latency_ms, client_ip, user_agent)


def ask(question: str, *, history: list[dict] | None = None,
        ministry_filter: str | None = None, session_id: str | None = None,
        client_ip: str = "", user_agent: str = "") -> dict:
    t0 = time.time()

    # ── Safety guard (deterministic, LLM-free) — abstain before any retrieval ──
    unsafe = guard.detect_unsafe(question)
    if unsafe:
        category, ref = unsafe
        contacts = trust._contacts(ref) if ref else None
        resp = {
            "answer": guard.DEFER_TEXT[category],
            "source_ministry": ref or [],
            "citations": [],
            "confident": False,
            "evidence_status": "declined",
            "decline_reason": category,
            "fallback_contact": contacts or None,
        }
        _log(question, session_id, ref or [], resp, int((time.time() - t0) * 1000),
             client_ip, user_agent)
        return resp

    # ── Intent gate — greetings, thanks, capability, off-topic ──
    intent = llm.classify_intent(question)
    chatty = llm.chatty_response(intent)
    if chatty is not None:
        resp = {
            "answer": chatty,
            "source_ministry": [],
            "citations": [],
            "confident": True,
            "evidence_status": "declined" if intent == "off_topic" else "answered",
            "fallback_contact": None,
        }
        _log(question, session_id, [], resp, int((time.time() - t0) * 1000),
             client_ip, user_agent)
        return resp

    # ── Normal RAG path ──
    search_q = llm.rewrite_query(question, history) if history else question
    detected = [ministry_filter] if ministry_filter else router.route(search_q)
    results = retrieval.search(search_q, detected or None, k=K)
    journey = journeys.match_journey(question)

    if not trust.assess(results):
        answering = detected or _distinct_ministries(results)
        resp = trust.fallback_response(question, answering)
        resp["evidence_status"] = "unsupported"
    else:
        answer = llm.generate(question, results, history=history, journey=journey)
        # Append web verification if the model hedged
        if _answer_is_hedged(answer):
            verify = _web_verify_if_uncertain(answer, question,
                                               detected or _distinct_ministries(results))
            if verify:
                answer += verify
        cites = _citations_from_answer(answer, results)
        resp = {
            "answer": answer,
            "source_ministry": _distinct_ministries(results),
            "citations": cites,
            "confident": True,
            "evidence_status": _evidence_status(
                confident=True, answer=answer, citations=cites),
            "service_journey": journey["id"] if journey else None,
            "fallback_contact": _contacts_safety_net(answer, detected or _distinct_ministries(results)),
        }

    _log(question, session_id, detected, resp, int((time.time() - t0) * 1000),
         client_ip, user_agent)
    return resp


def prepare_stream(question: str, history: list[dict] | None = None,
                   ministry_filter: str | None = None) -> dict:
    """Resolve guard + intent gate + query rewrite + route + retrieval + confidence."""

    # ── Safety guard first (no LLM) ──
    unsafe = guard.detect_unsafe(question)
    if unsafe:
        category, ref = unsafe
        contacts = trust._contacts(ref) if ref else None
        return {"declined": {
            "answer": guard.DEFER_TEXT[category],
            "source_ministry": ref or [],
            "fallback_contact": contacts or None,
            "decline_reason": category,
        }}

    # ── Intent gate, run in parallel with retrieval ──
    # classify_intent has a regex pre-gate, so obvious greetings/thanks/capability
    # resolve almost instantly — if so, short-circuit and skip retrieval. Otherwise
    # the LLM classify runs concurrently with route+retrieve below.
    classify_fut = _EXEC.submit(llm.classify_intent, question)
    try:
        intent = classify_fut.result(timeout=0.15)
        chatty = llm.chatty_response(intent)
        if chatty is not None:
            return {"intent": intent, "chatty_response": chatty,
                    "evidence_status": "declined" if intent == "off_topic" else "answered",
                    "confident": True, "history": history or []}
    except FuturesTimeout:
        pass  # classify is on the LLM — retrieve in parallel while it finishes

    search_q = llm.rewrite_query(question, history) if history else question
    detected = [ministry_filter] if ministry_filter else router.route(search_q)
    results = retrieval.search(search_q, detected or None, k=K)
    confident = trust.assess(results)
    intent = classify_fut.result()
    chatty = llm.chatty_response(intent)
    if chatty is not None:
        return {"intent": intent, "chatty_response": chatty,
                "evidence_status": "declined" if intent == "off_topic" else "answered",
                "confident": True, "history": history or []}
    return {"detected": detected, "results": results, "confident": confident,
            "journey": journeys.match_journey(question), "history": history or []}
