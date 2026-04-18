"""journal.append — Sprint 4 decision journal API.

New columns: ts, ticker, action, citations (JSONB). Existing columns
(event_id, severity, report_path, created_at) are preserved for Sprint 3
compatibility (see test_event_loop.py which still uses record_decision).

The ``append`` contract:

    append(conn, cycle_type, *, ticker=None, action=None,
           rationale=None, citations=None)

All rows land in ``decisions`` and can be queried back. ``citations`` is a
list of strings stored as JSONB — ``None`` stores SQL NULL.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest

from ria.journal import VALID_CYCLE_TYPES, append


pytestmark = pytest.mark.skipif(
    os.environ.get("RIA_SKIP_DB_TESTS") == "1",
    reason="DB-dependent tests skipped via RIA_SKIP_DB_TESTS=1",
)


@pytest.fixture
def conn():
    psycopg = pytest.importorskip("psycopg")
    from ria.db.conn import connect, ensure_schema
    try:
        c = connect()
    except psycopg.OperationalError as e:
        pytest.skip(f"Postgres unavailable: {e}")
    ensure_schema(c)
    ns = f"jn_{uuid.uuid4().hex[:8]}"
    yield c, ns
    with c.cursor() as cur:
        cur.execute(
            "DELETE FROM decisions WHERE rationale LIKE %s",
            (f"{ns}%",),
        )
    c.commit()
    c.close()


def test_append_planned_row_round_trip(conn):
    c, ns = conn
    append(
        c,
        "planned",
        ticker="AAPL",
        action="HOLD",
        rationale=f"{ns} weekly healthcheck",
        citations=["https://a.example/news/1", "accession:0001-25-000001"],
    )
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type, ticker, action, rationale, citations "
            "FROM decisions WHERE rationale LIKE %s ORDER BY id DESC LIMIT 1",
            (f"{ns}%",),
        )
        row = cur.fetchone()
    assert row is not None
    cycle_type, ticker, action, rationale, citations = row
    assert cycle_type == "planned"
    assert ticker == "AAPL"
    assert action == "HOLD"
    assert rationale.startswith(ns)
    # JSONB columns come back already decoded by psycopg
    if isinstance(citations, str):
        citations = json.loads(citations)
    assert citations == [
        "https://a.example/news/1",
        "accession:0001-25-000001",
    ]


def test_append_error_row(conn):
    c, ns = conn
    append(
        c,
        "error",
        ticker=None,
        action="ERROR",
        rationale=f"{ns} traceback",
        citations=None,
    )
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type, action, citations FROM decisions "
            "WHERE rationale LIKE %s",
            (f"{ns}%",),
        )
        rows = cur.fetchall()
    assert len(rows) == 1
    cycle, action, citations = rows[0]
    assert cycle == "error"
    assert action == "ERROR"
    assert citations is None


def test_append_all_cycle_types_accepted(conn):
    c, ns = conn
    for ct in VALID_CYCLE_TYPES:
        append(c, ct, rationale=f"{ns} {ct}")
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type FROM decisions WHERE rationale LIKE %s",
            (f"{ns}%",),
        )
        got = {r[0] for r in cur.fetchall()}
    assert got == set(VALID_CYCLE_TYPES)


def test_append_rejects_unknown_cycle_type(conn):
    c, _ns = conn
    with pytest.raises(ValueError, match="unknown cycle_type"):
        append(c, "not_a_cycle", rationale="x")


def test_append_ts_defaults_to_now(conn):
    """The ts column should auto-populate (DEFAULT NOW()) when not supplied."""
    c, ns = conn
    append(c, "planned", ticker="TSLA", action="WATCH", rationale=f"{ns} ts-check")
    with c.cursor() as cur:
        cur.execute(
            "SELECT ts FROM decisions WHERE rationale LIKE %s",
            (f"{ns}%",),
        )
        row = cur.fetchone()
    assert row is not None and row[0] is not None
