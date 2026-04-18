"""Decision journal + cooldown helpers.

Sprint 3 surface: ``record_decision``, ``within_cooldown``, ``mark_processed``.
Sprint 4 adds the normalised ``append`` API plus the decision-journal retrofit
in ``ria.agent.loop`` / ``ria.agent.event_loop`` for planned + error cycles.

The Sprint-3 columns (event_id / severity / report_path / created_at) are
preserved for backward compat — ``event_loop`` still calls ``record_decision``
and test_event_loop.py relies on those columns. Sprint-4 additions (ts,
ticker, action, citations JSONB) are applied via ``ALTER TABLE ADD COLUMN
IF NOT EXISTS`` in ``schema.sql``.

``append`` validates ``cycle_type`` against ``VALID_CYCLE_TYPES``. Unknown
values raise ``ValueError`` so a typo becomes a loud test failure instead
of silently corrupting the journal.
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Optional

from ria.agent.event import Event

# Canonical set per Sprint 4 session spec.
VALID_CYCLE_TYPES: tuple[str, ...] = (
    "planned",
    "interrupt_P0",
    "deferred_P1",
    "deferred_P2",
    "cooldown_skip",
    "error",
)


def append(
    conn: Any,
    cycle_type: str,
    *,
    ticker: Optional[str] = None,
    action: Optional[str] = None,
    rationale: Optional[str] = None,
    citations: Optional[Iterable[str]] = None,
    event_id: Optional[str] = None,
    severity: Optional[str] = None,
    report_path: Optional[Path | str] = None,
) -> None:
    """Insert one row into ``decisions``. Append-only, commits immediately.

    ``citations`` is stored as JSONB — pass ``None`` for SQL NULL, or an
    iterable of strings. ``event_id`` / ``severity`` / ``report_path`` are
    optional Sprint-3 compatibility fields; Sprint-4 planned/error cycles
    typically leave them unset.
    """
    if cycle_type not in VALID_CYCLE_TYPES:
        raise ValueError(
            f"unknown cycle_type {cycle_type!r} — expected one of {VALID_CYCLE_TYPES}"
        )
    citations_json = (
        json.dumps(list(citations)) if citations is not None else None
    )
    rp = str(report_path) if report_path is not None else None
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO decisions "
            "(cycle_type, event_id, severity, rationale, report_path, ticker, action, citations) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)",
            (cycle_type, event_id, severity, rationale, rp, ticker, action, citations_json),
        )
    conn.commit()


def record_decision(
    conn: Any,
    cycle_type: str,
    *,
    event: Optional[Event] = None,
    severity: Optional[str] = None,
    rationale: Optional[str] = None,
    report_path: Optional[Path] = None,
    ticker: Optional[str] = None,
    action: Optional[str] = None,
    citations: Optional[Iterable[str]] = None,
) -> None:
    """Sprint-3 compat wrapper. Delegates to ``append`` after extracting
    ``event_id`` and ``ticker`` from the Event object when available."""
    ev_id = event.event_id if event is not None else None
    tick = ticker
    if tick is None and event is not None and event.expected_affected_tickers:
        tick = event.expected_affected_tickers[0]
    append(
        conn,
        cycle_type,
        ticker=tick,
        action=action,
        rationale=rationale,
        citations=citations,
        event_id=ev_id,
        severity=severity,
        report_path=report_path,
    )


def within_cooldown(
    conn: Any,
    event_id: str,
    now: datetime,
    *,
    hours: int = 24,
) -> bool:
    with conn.cursor() as cur:
        cur.execute(
            "SELECT last_processed_at FROM event_cooldown WHERE event_id = %s",
            (event_id,),
        )
        row = cur.fetchone()
    if row is None:
        return False
    last = row[0]
    # Strip tz info for safe subtraction; we treat naive UTC == aware UTC.
    if last.tzinfo is not None and now.tzinfo is None:
        last = last.replace(tzinfo=None)
    if now.tzinfo is not None and last.tzinfo is None:
        now = now.replace(tzinfo=None)
    return (now - last) < timedelta(hours=hours)


def mark_processed(conn: Any, event_id: str, now: datetime) -> None:
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO event_cooldown (event_id, last_processed_at) "
            "VALUES (%s, %s) "
            "ON CONFLICT (event_id) DO UPDATE SET last_processed_at = EXCLUDED.last_processed_at",
            (event_id, now),
        )
    conn.commit()
