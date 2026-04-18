"""Decision journal + cooldown helpers.

Sprint 3 minimum surface — Sprint 4 will retrofit cost/token tracking.

Cooldown contract:

* ``within_cooldown(conn, event_id, now, hours)`` — returns ``True`` when the
  event was processed inside the rolling window.
* ``mark_processed(conn, event_id, now)`` — UPSERT-stamp the processing time.

Decision contract:

* ``record_decision(conn, cycle_type, event=None, severity=None,
  rationale=None, report_path=None)`` — single ``INSERT INTO decisions``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

from ria.agent.event import Event


def record_decision(
    conn: Any,
    cycle_type: str,
    *,
    event: Optional[Event] = None,
    severity: Optional[str] = None,
    rationale: Optional[str] = None,
    report_path: Optional[Path] = None,
) -> None:
    event_id = event.event_id if event is not None else None
    rp = str(report_path) if report_path is not None else None
    with conn.cursor() as cur:
        cur.execute(
            "INSERT INTO decisions (cycle_type, event_id, severity, rationale, report_path) "
            "VALUES (%s, %s, %s, %s, %s)",
            (cycle_type, event_id, severity, rationale, rp),
        )
    conn.commit()


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
