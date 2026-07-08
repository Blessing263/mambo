-- Migration: switch embeddings to OpenAI text-embedding-3-large (3072-dim).
--
-- Vectors from the old model (Qwen3-Embedding-8B, 4096-dim) are NOT comparable
-- with the new space, so every embedding is nulled and re-filled by
-- ingestion.embed_bulk (which now calls the OpenAI API — no GPU needed).
--
-- Notes for the live DB (inspected 2026-07-08):
--   * chunks.embedding is an UNCONSTRAINED `vector` there (it held 768/4096
--     test vectors); the ALTER below pins it to vector(3072) so a stray
--     wrong-dim vector can never sneak in again. All rows are NULL at that
--     point, so the ALTER is metadata-only and instant.
--   * official_response_chunks (reviewed-answer chunks) may not exist yet —
--     it ships with the admin-portal schema update — so that part is guarded.
--
-- Run:            psql "$DATABASE_URL" -f shared/db/migrations/2026-07-08_openai_3072.sql
-- Then re-embed:  uv run python -m ingestion.embed_bulk
--
-- Retrieval filters `embedding IS NOT NULL`, so the assistant degrades
-- gracefully (fewer/no chunks) during the re-embed window rather than mixing
-- vector spaces. Restart mambo-api (new embedding code) at the same time.

BEGIN;

-- Knowledge chunks
UPDATE chunks SET embedding = NULL, dim = NULL;
ALTER TABLE chunks ALTER COLUMN embedding TYPE vector(3072) USING NULL;

-- Reviewed-answer (official response) chunks — only if deployed
DO $$
BEGIN
    IF to_regclass('official_response_chunks') IS NOT NULL THEN
        UPDATE official_response_chunks SET embedding = NULL, dim = NULL;
        ALTER TABLE official_response_chunks
            ALTER COLUMN embedding TYPE vector(3072) USING NULL;
    END IF;
END $$;

COMMIT;
