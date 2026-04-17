-- Sprint 1 — pgvector schema for RIA.
-- docker-compose runs pgvector/pgvector:pg16 so the extension ships with the image.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS filings_chunks (
    id         SERIAL PRIMARY KEY,
    accession  TEXT NOT NULL,
    section    TEXT,
    text       TEXT NOT NULL,
    embedding  vector(384) NOT NULL,
    ts         TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS filings_chunks_embedding_idx
    ON filings_chunks USING hnsw (embedding vector_cosine_ops);
