"""Cached ministry metadata, read from the Knowledge Store (loaded from the Registry).

Used by the router (keywords), the trust layer (contacts/fallback), and the API
(/ministries for the webchat's picker).
"""

from __future__ import annotations

from functools import lru_cache

from shared.db import get_conn


@lru_cache(maxsize=1)
def ministries() -> list[dict]:
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute(
            """
            SELECT id, name, short_name, mandate, keywords, contact,
                   accent_color, sort_order, source_type, parent_ministry
            FROM ministries
            WHERE enabled = true
            ORDER BY sort_order;
            """
        )
        return cur.fetchall()


def by_id(ministry_id: str) -> dict | None:
    return {m["id"]: m for m in ministries()}.get(ministry_id)


def refresh() -> None:
    ministries.cache_clear()
