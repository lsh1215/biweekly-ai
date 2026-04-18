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

-- Sprint 3 — event off-cycle loop tables.
-- Sprint 4 retrofit adds ts/ticker/action/citations columns idempotently;
-- Sprint 3's event_loop keeps its original columns (event_id/severity/report_path).

CREATE TABLE IF NOT EXISTS decisions (
    id            SERIAL PRIMARY KEY,
    cycle_type    TEXT NOT NULL,
    event_id      TEXT,
    severity      TEXT,
    rationale     TEXT,
    report_path   TEXT,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Sprint 4 additive columns (IF NOT EXISTS keeps the migration idempotent
-- across reruns and between envs that started on the Sprint 3 schema).
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS ts        TIMESTAMPTZ NOT NULL DEFAULT NOW();
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS ticker    TEXT;
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS action    TEXT;
ALTER TABLE decisions ADD COLUMN IF NOT EXISTS citations JSONB;

CREATE INDEX IF NOT EXISTS decisions_cycle_type_idx ON decisions (cycle_type);
CREATE INDEX IF NOT EXISTS decisions_event_id_idx   ON decisions (event_id);

CREATE TABLE IF NOT EXISTS event_cooldown (
    event_id            TEXT PRIMARY KEY,
    last_processed_at   TIMESTAMPTZ NOT NULL
);
