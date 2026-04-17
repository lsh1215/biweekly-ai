"""Postgres connection helper.

DSN resolution: `$RIA_DATABASE_URL` overrides; default matches
`docker-compose.yml` (ria/ria@localhost:5432/ria).
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import psycopg
from pgvector.psycopg import register_vector

DEFAULT_DSN = "postgresql://ria:ria@localhost:5432/ria"
_SCHEMA_PATH = Path(__file__).resolve().parent / "schema.sql"


def dsn() -> str:
    return os.environ.get("RIA_DATABASE_URL", DEFAULT_DSN)


def connect(**kwargs: Any) -> psycopg.Connection:
    conn = psycopg.connect(dsn(), **kwargs)
    # `vector` extension must exist before register_vector; ensure_schema handles it.
    return conn


def ensure_schema(conn: psycopg.Connection) -> None:
    """Idempotently create extension, table, and HNSW index, then register codec."""
    with conn.cursor() as cur:
        cur.execute(_SCHEMA_PATH.read_text())
    conn.commit()
    register_vector(conn)
