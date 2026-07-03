"""Integration test: a FRESH schema built from schema.sql must accept every query
the code actually issues (loader insert, deferred-embed chunk, embed_bulk update,
query_log insert, catalog select). Skipped unless --integration / RUN_INTEGRATION
and a DB is reachable. Self-cleaning (dedicated ruzivo_pytest schema, autocommit)."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

SCHEMA_PATH = Path(__file__).resolve().parent.parent / "shared" / "db" / "schema.sql"
_DSN = "postgresql://ruzivo:ruzivo_local_dev@127.0.0.1:5432/ruzivo"


@pytest.mark.integration
def test_fresh_schema_accepts_all_code_queries():
    psycopg = pytest.importorskip("psycopg")
    pytest.importorskip("pgvector")

    dsn = os.environ.get("DATABASE_URL", _DSN)
    try:
        conn = psycopg.connect(dsn)
    except Exception:
        pytest.skip("Postgres not reachable")
    conn.autocommit = True  # DDL outside a transaction — avoids abort cascades

    schema = SCHEMA_PATH.read_text()
    try:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS ruzivo_pytest CASCADE")
            cur.execute("CREATE SCHEMA ruzivo_pytest")
            cur.execute("SET search_path TO ruzivo_pytest, public")
            cur.execute(schema)  # whole file (psycopg3 runs multi-statement DDL)

            # loader insert — source_type + parent_ministry
            cur.execute(
                "INSERT INTO ministries (id,name,short_name,mandate,keywords,domains,contact,"
                "accent_color,source_type,parent_ministry,sort_order,enabled) "
                "VALUES ('zimra','ZIMRA','ZIMRA','tax','{tax}'::text[],'{zimra.co.zw}'::text[],"
                "'{}'::jsonb,'#x','adjacent','finance',6,true)")
            # document + deferred-embed chunk (NULL embedding — the case NOT NULL broke)
            cur.execute(
                "INSERT INTO documents (ministry_id,source_url,title,doc_type,content_hash,"
                "page_count,ocr_used,raw_path,status) "
                "VALUES ('zimra','https://zimra.co.zw/x','Tax Guide','pdf','h',3,false,'r','active')")
            cur.execute(
                "INSERT INTO chunks (document_id,ministry_id,chunk_index,text,page,token_count,"
                "embedding,content_hash) SELECT id,'zimra',0,'txt',1,4,NULL,'h1' "
                "FROM documents WHERE source_url='https://zimra.co.zw/x'")
            # embed_bulk update — embedding + dim
            cur.execute(
                "UPDATE chunks SET embedding="
                "(SELECT ('['||string_agg('0',',')||']')::vector(4096) FROM generate_series(1,4096)),"
                "dim=4096 WHERE content_hash='h1'")
            # query_log insert — client_ip + user_agent
            cur.execute(
                "INSERT INTO query_log (session_id,question,detected_ministries,confident,answered,"
                "citations,latency_ms,client_ip,user_agent) "
                "VALUES ('s','q','{finance}'::text[],true,true,'[]'::jsonb,1,'1.1.1.1','UA')")
            # catalog select — source_type + parent_ministry
            cur.execute(
                "SELECT id,source_type,parent_ministry FROM ministries "
                "WHERE enabled=true ORDER BY sort_order")
            row = cur.fetchone()
            assert row[0] == "zimra" and row[1] == "adjacent" and row[2] == "finance"
    finally:
        with conn.cursor() as cur:
            cur.execute("DROP SCHEMA IF EXISTS ruzivo_pytest CASCADE")
        conn.close()
