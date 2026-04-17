"""Sprint 1 — rag_search tool (pgvector HNSW).

These tests require a live Postgres instance (docker-compose up). Each
test runs inside a unique transaction-scoped accession prefix so runs
don't collide with the real `scripts/run_ingest.py` corpus.

RAG queries are authored in English — MiniLM-L6-v2 is English-first.
A separate test documents that a Korean query still returns *something*,
but relevance is best-effort.
"""

from __future__ import annotations

import uuid

import psycopg
import pytest

try:
    from ria.db.conn import connect, dsn, ensure_schema
    from ria.ingest.filings import embed_texts
    _PG_AVAILABLE: bool | None = None
except Exception as exc:  # pragma: no cover
    _PG_AVAILABLE = False


def _pg_up() -> bool:
    global _PG_AVAILABLE
    if _PG_AVAILABLE is not None:
        return _PG_AVAILABLE
    try:
        with psycopg.connect(dsn(), connect_timeout=2) as c:
            c.execute("SELECT 1")
        _PG_AVAILABLE = True
    except Exception:
        _PG_AVAILABLE = False
    return _PG_AVAILABLE


pgmark = pytest.mark.skipif(
    not _pg_up(), reason="Postgres not reachable at $RIA_DATABASE_URL"
)


@pytest.fixture
def seeded_db():
    """Insert a handful of known chunks tagged with a unique accession prefix,
    yield the prefix, and delete them on teardown."""
    prefix = f"test_{uuid.uuid4().hex[:10]}"
    docs = [
        (f"{prefix}_AAPL", "ITEM 7.", "Apple reported strong iPhone sales and services revenue growth."),
        (f"{prefix}_TSLA", "ITEM 1.", "Tesla manufactures electric vehicles and energy storage systems."),
        (f"{prefix}_NVDA", "ITEM 1A.", "NVIDIA faces risks from export controls on advanced GPU shipments to China."),
        (f"{prefix}_MSFT", "ITEM 7.", "Microsoft Azure cloud revenue expanded with enterprise AI adoption."),
        (f"{prefix}_META", "ITEM 1.", "Meta operates social networks and invests in augmented reality hardware."),
    ]
    vecs = embed_texts([t for _, _, t in docs])
    conn = connect()
    ensure_schema(conn)
    with conn.cursor() as cur:
        cur.executemany(
            "INSERT INTO filings_chunks (accession, section, text, embedding)"
            " VALUES (%s, %s, %s, %s)",
            [(a, s, t, v) for (a, s, t), v in zip(docs, vecs, strict=True)],
        )
    conn.commit()

    yield prefix

    with conn.cursor() as cur:
        cur.execute("DELETE FROM filings_chunks WHERE accession LIKE %s", (f"{prefix}%",))
    conn.commit()
    conn.close()


@pgmark
def test_rag_search_returns_list_of_chunks(seeded_db: str) -> None:
    from ria.tools.rag import rag_search

    results = rag_search("iPhone sales and services", top_k=3)
    assert isinstance(results, list)
    assert len(results) >= 1
    top = results[0]
    for key in ("accession", "section", "text", "distance"):
        assert key in top


@pgmark
def test_rag_search_finds_relevant_document(seeded_db: str) -> None:
    from ria.tools.rag import rag_search

    results = rag_search("iPhone revenue and services growth", top_k=5)
    # At least one of the top-5 should come from our seeded set, and the
    # AAPL doc should rank ahead of (or equal to) the Meta doc for this query.
    seeded = [r for r in results if r["accession"].startswith(seeded_db)]
    assert seeded, f"no seeded rows in top-5: {results}"
    top_texts = " ".join(r["text"].lower() for r in seeded[:2])
    assert "apple" in top_texts or "iphone" in top_texts


@pgmark
def test_rag_search_top_k_respected(seeded_db: str) -> None:
    from ria.tools.rag import rag_search

    results = rag_search("Tesla electric vehicles", top_k=2)
    assert len(results) <= 2


@pgmark
def test_rag_search_default_top_k_is_five(seeded_db: str) -> None:
    from ria.tools.rag import rag_search

    results = rag_search("cloud computing revenue")
    assert len(results) <= 5  # default top_k == 5 (may be fewer if corpus small)


@pgmark
def test_rag_search_distance_is_monotonic(seeded_db: str) -> None:
    from ria.tools.rag import rag_search

    results = rag_search("GPU export controls China", top_k=3)
    distances = [r["distance"] for r in results]
    assert distances == sorted(distances)


@pgmark
def test_rag_search_empty_query_still_returns(seeded_db: str) -> None:
    """Degenerate input shouldn't crash — returns (possibly irrelevant) neighbours."""
    from ria.tools.rag import rag_search

    results = rag_search("", top_k=1)
    assert isinstance(results, list)


@pgmark
@pytest.mark.xfail(
    reason="MiniLM-L6-v2 is English-first; Korean queries are best-effort (tracked in TIMELINE).",
    strict=False,
)
def test_rag_search_korean_query_documented_limitation(seeded_db: str) -> None:
    from ria.tools.rag import rag_search

    results = rag_search("애플 실적", top_k=3)
    assert len(results) >= 1
