"""Chunking — split extracted pages into retrieval-sized pieces that keep their
page reference (so citations can say "p.12"). Paragraph-aware, with overlap for
context continuity, and a hard-split safety net for very long paragraphs.
"""

from __future__ import annotations

import re

TARGET_CHARS = 2000      # ~500 tokens — good granularity for precise citations
OVERLAP_CHARS = 200      # continuity between adjacent chunks
_PARA_SPLIT = re.compile(r"\n\s*\n+")


def _paragraphs(text: str) -> list[str]:
    parts = [p.strip() for p in _PARA_SPLIT.split(text) if p.strip()]
    return parts or ([text.strip()] if text.strip() else [])


def chunk_pages(
    pages: list[tuple[int | None, str]],
    *,
    target: int = TARGET_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[dict]:
    """Return chunks: [{'chunk_index', 'text', 'page', 'section'}]."""
    chunks: list[dict] = []

    def emit(page: int | None, text: str) -> None:
        text = text.strip()
        if not text:
            return
        section = text.split("\n", 1)[0][:120] if text else None
        chunks.append({"chunk_index": len(chunks), "text": text,
                       "page": page, "section": section})

    for page_no, page_text in pages:
        if not page_text or not page_text.strip():
            continue
        buf = ""
        for para in _paragraphs(page_text):
            # A single oversized paragraph: hard-split it.
            while len(para) > int(target * 1.5):
                head, para = para[:target], para[target - overlap:]
                if buf:
                    emit(page_no, buf)
                    buf = ""
                emit(page_no, head)
            if len(buf) + len(para) + 1 <= target:
                buf = f"{buf}\n{para}".strip()
            else:
                if buf:
                    emit(page_no, buf)
                tail = buf[-overlap:] if buf else ""
                buf = f"{tail}\n{para}".strip() if tail else para
        if buf:
            emit(page_no, buf)

    # Re-number after the fact so chunk_index is contiguous across pages.
    for i, ch in enumerate(chunks):
        ch["chunk_index"] = i
    return chunks
