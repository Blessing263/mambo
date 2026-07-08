"""The trust layer — government-grade guardrails enforced in the brain.

  * confidence threshold: don't answer if retrieval is weak — fall back honestly,
  * citations: built from the actual retrieved sources,
  * fallback: route the citizen to the right ministry's real contact details,
  * topic-lock: if nothing matches and no ministry is implicated, decline politely.
"""

from __future__ import annotations

from shared.config import settings
from .catalog import by_id

CONFIDENCE_THRESHOLD = settings.confidence_threshold


def assess(results: list[dict]) -> bool:
    return bool(results) and results[0]["score"] >= CONFIDENCE_THRESHOLD


def cite(result: dict) -> dict:
    text = (result.get("text") or "").strip()
    snippet = (text[:157] + "…") if len(text) > 160 else (text or None)
    if result.get("source_kind") == "official_response":
        cites = result.get("response_citations") or []
        first = cites[0] if isinstance(cites, list) and cites else {}
        return {
            "title": first.get("title") or result.get("doc_title"),
            "page": None,
            "url": first.get("url") or result.get("source_url"),
            "ministry": result.get("ministry_id"),
            "snippet": snippet,
            "doc_type": "web",
        }
    url = result.get("source_url") or ""
    return {
        "title": result.get("doc_title"),
        "page": result.get("page"),
        "url": result.get("source_url"),
        "ministry": result.get("ministry_id"),
        "snippet": snippet,
        "doc_type": "pdf" if url.lower().endswith(".pdf") else "web",
    }


def top_citations(results: list[dict], n: int = 3) -> list[dict]:
    return [cite(r) for r in results[:n]]


def _contacts(ministry_ids: list[str]) -> list[dict]:
    out = []
    for mid in ministry_ids:
        m = by_id(mid)
        if m:
            out.append({"ministry": m["short_name"], **(m["contact"] or {})})
    return out


def fallback_response(question: str, ministry_ids: list[str]) -> dict:
    contacts = _contacts(ministry_ids)
    # Try web verification for extra context (silently fails if no key)
    enrich = None
    try:
        from .verify import verify_enrich  # noqa: PLC0415
        enrich = verify_enrich(question, ministry_ids=ministry_ids)  # full question, not search query
    except Exception:
        pass

    if contacts:
        names = ", ".join(c["ministry"] for c in contacts)
        # Warm, helpful fallback — acknowledges what was asked, states honestly
        # what the documents cover, and gives a clear path forward.
        answer = (
            f"I've searched the official documents, but the specific procedure "
            f"you've asked about isn't covered in what I currently hold.\n\n"
            f"This falls under the **{names}** "
            f"{'ministry' if len(contacts) == 1 else 'ministries'}. "
            f"Many detailed procedures — like replacing a lost ID — are handled "
            f"at the relevant office rather than published online. "
            f"{'Their' if len(contacts) == 1 else 'Their'} contact details are "
            f"below — you can call, visit, or message them for the exact steps, "
            f"forms and fees."
        ) + (enrich or "")
    else:
        answer = (
            "I can only answer questions about Zimbabwe government ministries and "
            "the public services they provide, drawing strictly on official "
            "documents. I don't have information on that. Could you rephrase it, "
            "or tell me which ministry or service it relates to?"
        )
    return {
        "answer": answer,
        "source_ministry": ministry_ids,
        "citations": [],
        "confident": False,
        "fallback_contact": contacts or None,
    }
