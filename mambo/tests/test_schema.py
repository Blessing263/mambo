"""Schema drift regression — the columns the code references must exist in schema.sql,
and embeddings must be nullable (deferred-embedding workflow)."""

from __future__ import annotations

from pathlib import Path

SCHEMA = (Path(__file__).resolve().parent.parent / "shared" / "db" / "schema.sql").read_text()


def _table(name: str) -> str:
    return SCHEMA.split(f"CREATE TABLE IF NOT EXISTS {name}")[1].split(");")[0]


def test_ministries_has_source_type_and_parent():
    block = _table("ministries")
    assert "source_type" in block
    assert "parent_ministry" in block


def test_query_log_has_client_ip_and_user_agent():
    block = _table("query_log")
    assert "client_ip" in block
    assert "user_agent" in block


def test_chunks_embedding_is_nullable():
    block = _table("chunks")
    assert "vector(3072)" in block  # OpenAI text-embedding-3-large
    emb_line = next(l for l in block.splitlines() if "embedding" in l)
    assert "NOT NULL" not in emb_line          # was NOT NULL — broke deferred embedding


def test_chunks_has_dim_and_deferred_embed_indexes():
    assert "dim" in SCHEMA
    assert "idx_chunks_pending" in SCHEMA      # WHERE embedding IS NULL
    assert "idx_chunks_dim" in SCHEMA          # WHERE embedding IS NOT NULL


def test_admin_staff_table():
    block = _table("staff")
    assert "password_hash" in block
    assert "email" in block and "ministry_id" in block


def test_staff_sessions_table():
    assert "CREATE TABLE IF NOT EXISTS staff_sessions" in SCHEMA
    assert "idx_staff_sessions_staff" in SCHEMA


def test_reviewed_answers_has_question_norm():
    assert "question_norm" in SCHEMA
    assert "idx_reviewed_enabled" in SCHEMA
