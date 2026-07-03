-- Ruzivo — Knowledge Store schema (Postgres 16 + pgvector)
-- The seam between Ingestion (writes) and RAG (reads). Every chunk is tagged by
-- ministry for routing, and carries full provenance so every citation is verifiable.
--
-- Embeddings: Qwen3-Embedding-8B, 4096 dimensions.
-- NOTE: pgvector 0.6.0 caps ANN indexes (ivfflat/hnsw) at 2000 dims, so at 4096 we
-- use EXACT nearest-neighbour search (no ANN index). This is fast and accurate at
-- demo scale (thousands of chunks). Scale path: upgrade pgvector >=0.7 and store as
-- halfvec(4096) for an HNSW index, or reduce dims via Matryoshka truncation.

CREATE EXTENSION IF NOT EXISTS vector;

-- ─────────────────────────────────────────────────────────────────────────────
-- Ministries — mirror of the Registry (the source of truth lives in registry/).
-- Loaded from registry/ministries.json so RAG can join/filter without reading files.
-- source_type distinguishes core ministries from adjacent official bodies (agencies
-- and trusted legal sources); parent_ministry links an adjacent source to its
-- overseeing ministry (e.g. ZIMRA -> finance, ZIMSEC -> education).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS ministries (
    id              text PRIMARY KEY,                 -- e.g. 'ict'
    name            text        NOT NULL,
    short_name      text        NOT NULL,             -- e.g. 'ICT'
    mandate         text        NOT NULL,
    keywords        text[]      NOT NULL DEFAULT '{}',-- routing hints
    domains         text[]      NOT NULL DEFAULT '{}',-- allow-list (scrape scope)
    contact         jsonb       NOT NULL DEFAULT '{}',-- phone/whatsapp/address/hours
    accent_color    text,                             -- per-ministry theming
    source_type     text        NOT NULL DEFAULT 'ministry',  -- ministry | adjacent
    parent_ministry text,                               -- overseeing ministry id (adjacent sources)
    sort_order      int         NOT NULL DEFAULT 100,
    enabled         boolean     NOT NULL DEFAULT true,
    created_at      timestamptz NOT NULL DEFAULT now(),
    updated_at      timestamptz NOT NULL DEFAULT now()
);

-- ─────────────────────────────────────────────────────────────────────────────
-- Documents — one row per official source document discovered & ingested.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS documents (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ministry_id    text        NOT NULL REFERENCES ministries(id) ON DELETE CASCADE,
    source_url     text        NOT NULL,           -- canonical official URL (provenance)
    title          text        NOT NULL,
    doc_type       text        NOT NULL DEFAULT 'unknown', -- pdf | html | docx
    published_date date,                           -- if discoverable
    fetched_at     timestamptz NOT NULL DEFAULT now(),
    content_hash   text        NOT NULL,           -- for incremental refresh / dedupe
    raw_path       text,                           -- where the raw original is stored
    page_count     int,
    ocr_used       boolean     NOT NULL DEFAULT false,
    status         text        NOT NULL DEFAULT 'active', -- active | superseded | removed
    created_at     timestamptz NOT NULL DEFAULT now(),
    UNIQUE (source_url)
);
CREATE INDEX IF NOT EXISTS idx_documents_ministry ON documents (ministry_id);
CREATE INDEX IF NOT EXISTS idx_documents_hash     ON documents (content_hash);

-- ─────────────────────────────────────────────────────────────────────────────
-- Chunks — retrieval-sized pieces with embeddings. ministry_id denormalised for
-- fast scoped search by the router.
--
-- embedding is NULLABLE: ingestion can store chunks without vectors and fill them
-- later via ingestion.embed_bulk (the deferred-embedding / GPU workflow). Retrieval
-- filters `embedding IS NOT NULL` so pending chunks are never searched. `dim` labels
-- the embedding dimension (e.g. 4096) for the multi-dim / migration case.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS chunks (
    id           uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id  uuid        NOT NULL REFERENCES documents(id) ON DELETE CASCADE,
    ministry_id  text        NOT NULL REFERENCES ministries(id) ON DELETE CASCADE,
    chunk_index  int         NOT NULL,             -- order within the document
    text         text        NOT NULL,
    page         int,                              -- for "Source: …, p.12"
    section      text,                             -- nearest heading, if known
    token_count  int,
    embedding    vector(4096),                     -- nullable; NULL = pending embed
    content_hash text        NOT NULL,
    created_at   timestamptz NOT NULL DEFAULT now(),
    dim          smallint                          -- embedding dimension label (e.g. 4096)
);
CREATE INDEX IF NOT EXISTS idx_chunks_ministry ON chunks (ministry_id);
CREATE INDEX IF NOT EXISTS idx_chunks_document ON chunks (document_id);
-- Deferred-embedding workflow: fast lookups for pending (NULL) and embedded rows.
CREATE INDEX IF NOT EXISTS idx_chunks_pending ON chunks (id) WHERE embedding IS NULL;
CREATE INDEX IF NOT EXISTS idx_chunks_dim     ON chunks (dim)  WHERE embedding IS NOT NULL;
-- No vector ANN index at 4096 dims (pgvector 0.6.0 limit); exact search via <=>.

-- ─────────────────────────────────────────────────────────────────────────────
-- Query log — feeds analytics ("what citizens ask most") + quality review.
-- Public questions only; no private/personal data is solicited. client_ip /
-- user_agent are retention-bounded operational fields — see the privacy &
-- data-protection policy (PII minimisation, retention window, deletion workflow).
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS query_log (
    id                 uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    asked_at           timestamptz NOT NULL DEFAULT now(),
    session_id         text,
    question           text        NOT NULL,
    lang               text        NOT NULL DEFAULT 'en',
    detected_ministries text[]     NOT NULL DEFAULT '{}',
    confident          boolean,
    answered           boolean,
    citations          jsonb       NOT NULL DEFAULT '[]',
    latency_ms         int,
    feedback           smallint,                     -- +1 / -1 / null
    client_ip          varchar(45),                  -- best-effort real IP (retention-bounded)
    user_agent         varchar(500)                  -- UA string (retention-bounded)
);
CREATE INDEX IF NOT EXISTS idx_query_log_asked ON query_log (asked_at);

-- ─────────────────────────────────────────────────────────────────────────────
-- Reviewed-answer cache (Phase 2) — human-vetted answers for top questions so the
-- most-seen replies per ministry are guaranteed perfect. Present now for forward
-- compatibility; unused until curated.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS reviewed_answers (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ministry_id text REFERENCES ministries(id) ON DELETE CASCADE,
    question    text        NOT NULL,
    answer      text        NOT NULL,
    citations   jsonb       NOT NULL DEFAULT '[]',
    enabled     boolean     NOT NULL DEFAULT true,
    updated_at  timestamptz NOT NULL DEFAULT now()
);

-- Fast exact-match lookup for the reviewed-answer short-circuit (normalised question).
ALTER TABLE reviewed_answers ADD COLUMN IF NOT EXISTS question_norm text;
CREATE INDEX IF NOT EXISTS idx_reviewed_enabled
    ON reviewed_answers (ministry_id, question_norm) WHERE enabled;
CREATE INDEX IF NOT EXISTS idx_reviewed_ministry ON reviewed_answers (ministry_id);

-- ─────────────────────────────────────────────────────────────────────────────
-- Admin portal (Track 3) — ministry-staff auth + reviewed-answer curation.
-- staff: one row per ministry agent (scoped to their ministry_id).
-- staff_sessions: opaque session tokens (httpOnly cookie), revocable.
-- ─────────────────────────────────────────────────────────────────────────────
CREATE TABLE IF NOT EXISTS staff (
    id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    ministry_id   text REFERENCES ministries(id) ON DELETE CASCADE,
    email         text UNIQUE NOT NULL,
    name          text        NOT NULL,
    role          text        NOT NULL DEFAULT 'agent',   -- agent | supervisor
    password_hash text        NOT NULL,
    created_at    timestamptz NOT NULL DEFAULT now(),
    last_login_at timestamptz
);

CREATE TABLE IF NOT EXISTS staff_sessions (
    token      text PRIMARY KEY,
    staff_id   uuid        NOT NULL REFERENCES staff(id) ON DELETE CASCADE,
    expires_at timestamptz NOT NULL,
    created_at timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS idx_staff_sessions_staff   ON staff_sessions (staff_id);
CREATE INDEX IF NOT EXISTS idx_staff_sessions_expires ON staff_sessions (expires_at);
