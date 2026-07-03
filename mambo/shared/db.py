"""Knowledge Store access (Postgres + pgvector).

A thin layer over psycopg3 with the pgvector adapter registered so Python lists /
numpy arrays round-trip to the `vector(4096)` column transparently.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row

from .config import settings


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Yield a connection with dict rows and the pgvector adapter registered."""
    conn = psycopg.connect(settings.database_url, row_factory=dict_row)
    try:
        register_vector(conn)
        yield conn
    finally:
        conn.close()


def healthcheck() -> dict:
    """Quick sanity check: extension present, table counts."""
    with get_conn() as conn, conn.cursor() as cur:
        cur.execute("SELECT extversion FROM pg_extension WHERE extname='vector';")
        row = cur.fetchone()
        pgvector_version = row["extversion"] if row else None
        counts = {}
        for table in ("ministries", "documents", "chunks"):
            cur.execute(f"SELECT count(*) AS n FROM {table};")
            counts[table] = cur.fetchone()["n"]
    return {"pgvector": pgvector_version, "counts": counts}
