"""Load registry/ministries.json into the `ministries` table (idempotent upsert).

The JSON file is the human-edited source of truth and the scrape allow-list; this
script syncs it into Postgres so the RAG router and webchat can query it directly.

Run:  uv run python registry/load_registry.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from shared.db import get_conn  # noqa: E402

REGISTRY_PATH = Path(__file__).resolve().parent / "ministries.json"

UPSERT = """
INSERT INTO ministries
    (id, name, short_name, mandate, keywords, domains, contact,
     accent_color, source_type, parent_ministry, sort_order, enabled, updated_at)
VALUES
    (%(id)s, %(name)s, %(short_name)s, %(mandate)s, %(keywords)s, %(domains)s,
     %(contact)s, %(accent_color)s, %(source_type)s, %(parent_ministry)s,
     %(sort_order)s, %(enabled)s, now())
ON CONFLICT (id) DO UPDATE SET
    name            = EXCLUDED.name,
    short_name      = EXCLUDED.short_name,
    mandate         = EXCLUDED.mandate,
    keywords        = EXCLUDED.keywords,
    domains         = EXCLUDED.domains,
    contact         = EXCLUDED.contact,
    accent_color    = EXCLUDED.accent_color,
    source_type     = EXCLUDED.source_type,
    parent_ministry = EXCLUDED.parent_ministry,
    sort_order      = EXCLUDED.sort_order,
    enabled         = EXCLUDED.enabled,
    updated_at      = now();
"""


def load() -> int:
    data = json.loads(REGISTRY_PATH.read_text())
    ministries = data["ministries"]
    with get_conn() as conn, conn.cursor() as cur:
        for m in ministries:
            cur.execute(
                UPSERT,
                {
                    "id": m["id"],
                    "name": m["name"],
                    "short_name": m["short_name"],
                    "mandate": m["mandate"],
                    "keywords": m.get("keywords", []),
                    "domains": m.get("domains", []),
                    "contact": json.dumps(m.get("contact", {})),
                    "accent_color": m.get("accent_color"),
                    "source_type": m.get("source_type", "ministry"),
                    "parent_ministry": m.get("parent_ministry"),
                    "sort_order": m.get("sort_order", 100),
                    "enabled": m.get("enabled", True),
                },
            )
        conn.commit()
    return len(ministries)


if __name__ == "__main__":
    n = load()
    print(f"Upserted {n} ministries from {REGISTRY_PATH.name} (registry version "
          f"{json.loads(REGISTRY_PATH.read_text())['version']}).")
