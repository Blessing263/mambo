"""Knowledge Store access (Postgres + pgvector).

Connection pooling via psycopg_pool, with the pgvector adapter registered on
every checked-out connection so Python lists / numpy arrays round-trip to the
`vector(4096)` column transparently.
"""

from __future__ import annotations

from contextlib import contextmanager
import threading
from typing import Iterator

import psycopg
from pgvector.psycopg import register_vector
from psycopg.rows import dict_row
from psycopg_pool import ConnectionPool

from .config import settings

_pool: ConnectionPool | None = None
_pool_lock = threading.Lock()


def _get_pool() -> ConnectionPool:
    global _pool
    if _pool is None:
        with _pool_lock:
            if _pool is None:
                pool = ConnectionPool(
                    settings.database_url,
                    min_size=2,
                    max_size=10,
                    timeout=30,
                    open=False,
                    kwargs={"row_factory": dict_row},
                    configure=register_vector,
                )
                pool.open()
                _pool = pool
    return _pool


@contextmanager
def get_conn() -> Iterator[psycopg.Connection]:
    """Yield a pooled connection with dict rows and the pgvector adapter registered."""
    with _get_pool().connection() as conn:
        yield conn


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
