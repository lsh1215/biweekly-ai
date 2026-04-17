"""Semantic retrieval over the filings corpus via pgvector HNSW.

MiniLM-L6-v2 (384-dim) embeds both the corpus (at ingest time) and the
query (here). Cosine distance is the ranking metric — HNSW index is
built with `vector_cosine_ops` at default parameters (m=16, ef=64).

RAG queries should be authored in English — see TIMELINE for the Korean
query limitation note.
"""

from __future__ import annotations

from typing import TypedDict

from ria.db.conn import connect, ensure_schema
from ria.ingest.filings import embed_texts


class Chunk(TypedDict):
    accession: str
    section: str | None
    text: str
    distance: float


def rag_search(query: str, top_k: int = 5) -> list[Chunk]:
    """Return the `top_k` nearest filings_chunks rows (cosine distance).

    Returns fewer rows when the corpus is smaller than `top_k`. Never
    raises on empty queries — callers may legitimately send whitespace
    while assembling agent tool-call arguments.
    """
    if top_k <= 0:
        return []
    [vec] = embed_texts([query or " "])

    conn = connect()
    try:
        ensure_schema(conn)
        with conn.cursor() as cur:
            cur.execute(
                "SELECT accession, section, text, embedding <=> %s::vector AS distance"
                " FROM filings_chunks"
                " ORDER BY embedding <=> %s::vector"
                " LIMIT %s",
                (vec, vec, top_k),
            )
            rows = cur.fetchall()
    finally:
        conn.close()

    return [
        {"accession": r[0], "section": r[1], "text": r[2], "distance": float(r[3])}
        for r in rows
    ]
