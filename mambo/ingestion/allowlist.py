"""The scrape allow-list — derived from the Ministry Registry.

Mambo may only ever fetch from the exact hosts listed in the registry.
This is the trust boundary for ingestion: only allow-listed sources in.

The database copy (synced by registry/load_registry.py) is preferred; when no
database is reachable — e.g. save-only acquisition on a laptop — we fall back
to registry/ministries.json, which is the human-edited source of truth the DB
is loaded from, so the trust boundary is identical.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import urlparse

REGISTRY_PATH = Path(__file__).resolve().parent.parent / "registry" / "ministries.json"


def host_of(url: str) -> str:
    return (urlparse(url).hostname or "").lower()


def _mapping_from_db() -> dict[str, str]:
    from shared.db import get_conn  # noqa: PLC0415

    mapping: dict[str, str] = {}
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT id, domains FROM ministries WHERE enabled = true;")
        for row in cur.fetchall():
            for domain in row["domains"]:
                mapping[domain.lower().lstrip(".")] = row["id"]
    return mapping


def _mapping_from_registry_file() -> dict[str, str]:
    mapping: dict[str, str] = {}
    data = json.loads(REGISTRY_PATH.read_text())
    for m in data["ministries"]:
        if not m.get("enabled", True):
            continue
        for domain in m.get("domains", []):
            mapping[domain.lower().lstrip(".")] = m["id"]
    return mapping


@lru_cache(maxsize=1)
def _host_to_ministry() -> dict[str, str]:
    # RUZIVO_ALLOWLIST=file skips the DB entirely (saves the pool timeout on
    # machines without Postgres); ingestion.acquire sets this for itself.
    if os.environ.get("RUZIVO_ALLOWLIST", "").lower() == "file":
        return _mapping_from_registry_file()
    try:
        return _mapping_from_db()
    except Exception:  # noqa: BLE001 — no DB here (e.g. acquire-only laptop)
        return _mapping_from_registry_file()


def allowed_hosts() -> frozenset[str]:
    return frozenset(_host_to_ministry().keys())


def is_allowed(url: str) -> bool:
    """True only if the URL's host is an exact allow-listed host from the registry."""
    return host_of(url) in allowed_hosts()


def ministry_for_url(url: str) -> str | None:
    return _host_to_ministry().get(host_of(url))
