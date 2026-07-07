"""The scrape allow-list — derived from the Ministry Registry in the database.

Mambo may only ever fetch from the exact hosts listed in the registry.
This is the trust boundary for ingestion: only allow-listed sources in.
"""

from __future__ import annotations

from functools import lru_cache
from urllib.parse import urlparse

from shared.db import get_conn


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


@lru_cache(maxsize=1)
def _host_to_ministry() -> dict[str, str]:
    mapping: dict[str, str] = {}
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, domains FROM ministries WHERE enabled = true;")
        for row in cur.fetchall():
            for domain in row["domains"]:
                mapping[domain.lower().lstrip(".")] = row["id"]
    return mapping


def allowed_hosts() -> frozenset[str]:
    return frozenset(_host_to_ministry().keys())


def is_allowed(url: str) -> bool:
    """True only if the URL's host is an exact allow-listed host from the registry."""
    return host_of(url) in allowed_hosts()


def ministry_for_url(url: str) -> str | None:
    return _host_to_ministry().get(host_of(url))
