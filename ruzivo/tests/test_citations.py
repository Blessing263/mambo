"""Citation extraction + dedup from a generated answer (pure function)."""

from __future__ import annotations

from rag import service

CTX = [
    {"doc_title": "AI Strategy", "page": 12, "source_url": "https://ict.gov.zw/a", "ministry_id": "ict"},
    {"doc_title": "Data Protection", "page": 4, "source_url": "https://ict.gov.zw/b", "ministry_id": "ict"},
    {"doc_title": "Broadband Plan", "page": 7, "source_url": "https://ict.gov.zw/c", "ministry_id": "ict"},
]


def test_markers_map_to_contexts():
    c = service._citations_from_answer("See [1] and also [3].", CTX)
    assert [x["title"] for x in c] == ["AI Strategy", "Broadband Plan"]


def test_dedup_same_url_ignoring_scheme_and_fragment():
    dup = [
        {"doc_title": "A", "page": 1, "source_url": "https://x.gov.zw/p", "ministry_id": "ict"},
        {"doc_title": "A2", "page": 2, "source_url": "http://x.gov.zw/p#sec", "ministry_id": "ict"},
    ]
    c = service._citations_from_answer("see [1] [2]", dup)
    assert len(c) == 1


def test_dedup_same_title_different_url():
    dup = [
        {"doc_title": "Same Title", "page": 1, "source_url": "https://x.gov.zw/a", "ministry_id": "ict"},
        {"doc_title": "Same Title", "page": 2, "source_url": "https://y.gov.zw/b", "ministry_id": "ict"},
    ]
    c = service._citations_from_answer("see [1] [2]", dup)
    assert len(c) == 1


def test_no_markers_falls_back_to_top():
    c = service._citations_from_answer("no markers here", CTX)
    assert len(c) >= 1            # top_citations fallback


def test_out_of_range_marker_ignored():
    c = service._citations_from_answer("see [9]", CTX)   # only 3 contexts
    assert len(c) >= 1           # falls back to top citations
