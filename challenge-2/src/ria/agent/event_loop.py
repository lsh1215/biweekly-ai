"""Event off-cycle loop.

Drains a directory of synthetic event JSON files, classifies each via Haiku,
and — for **P0 only (v1)** — runs the interrupt agent to emit a markdown
report. P1/P2 events are journaled (`deferred_P1` / `deferred_P2`) so they
appear in the next planned cycle's news aggregation. Duplicate events
(identical `event_id`) inside the cooldown window get a `cooldown_skip`
journal entry and are not re-processed.

Pure-Python core: severity gate + cooldown + ordering. Test-friendly:

* ``now_fn`` injected (default ``datetime.utcnow``); tests can advance the
  simulated clock to validate the 24h cooldown threshold.
* ``classify_fn`` and ``agent_runner`` injected so unit tests don't need
  Anthropic or even the agent-loop module.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from ria.agent.event import Event
from ria.journal import mark_processed, record_decision, within_cooldown
from ria.models import Portfolio
from ria.tools.classify import ClassifierResult, classify_severity

logger = logging.getLogger(__name__)

COOLDOWN_HOURS = 24


@dataclass
class EventDecision:
    event_id: str
    cycle_type: str  # interrupt_P0 | deferred_P1 | deferred_P2 | cooldown_skip
    severity: Optional[str] = None
    rationale: Optional[str] = None
    report_path: Optional[Path] = None


@dataclass
class EventLoopReport:
    decisions: list[EventDecision] = field(default_factory=list)

    def by_cycle(self, cycle_type: str) -> list[EventDecision]:
        return [d for d in self.decisions if d.cycle_type == cycle_type]


def load_events(queue_dir: Path) -> list[Event]:
    """Read every ``*.json`` under queue_dir and sort by ``ts_utc`` ascending."""
    queue_dir = Path(queue_dir)
    events = [Event.from_path(fp) for fp in sorted(queue_dir.glob("*.json"))]
    events.sort(key=lambda e: e.ts_utc)
    return events


def _default_classifier(event: Event, portfolio: Portfolio) -> ClassifierResult:
    return classify_severity(event, portfolio)


def process_all(
    queue_dir: Path,
    portfolio: Portfolio,
    out_dir: Path,
    *,
    db_conn: Any,
    now_fn: Callable[[], datetime] = datetime.utcnow,
    classify_fn: Callable[[Event, Portfolio], ClassifierResult] = _default_classifier,
    agent_runner: Optional[Callable[[Event, Portfolio, Path, ClassifierResult], Optional[Path]]] = None,
    cooldown_hours: int = COOLDOWN_HOURS,
) -> EventLoopReport:
    """Drain the queue, applying severity gate + cooldown + journal hooks.

    Parameters
    ----------
    queue_dir : Path
        Directory containing synthetic event JSON files.
    portfolio : Portfolio
        Used by the classifier to decide direct-hit (P0) vs macro (P1).
    out_dir : Path
        Where the agent_runner is expected to write interrupt reports.
    db_conn : psycopg.Connection
        Used for cooldown lookup + journal inserts.
    now_fn : callable, optional
        Returns the "current" datetime — injectable for tests.
    classify_fn : callable, optional
        Replace for tests / replay mode.
    agent_runner : callable, optional
        Required for P0 events — returns the written report Path.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    report = EventLoopReport()
    events = load_events(queue_dir)

    for evt in events:
        now = now_fn()

        # --- cooldown gate ---------------------------------------------------
        if within_cooldown(db_conn, evt.event_id, now, hours=cooldown_hours):
            record_decision(
                db_conn,
                "cooldown_skip",
                event=evt,
                rationale=f"event_id seen within {cooldown_hours}h",
            )
            report.decisions.append(
                EventDecision(event_id=evt.event_id, cycle_type="cooldown_skip")
            )
            logger.info("cooldown_skip event_id=%s", evt.event_id)
            continue

        # --- classification --------------------------------------------------
        classification = classify_fn(evt, portfolio)
        sev = classification.severity

        # --- severity gate (v1: P0 only triggers interrupt) -----------------
        if sev == "P0":
            if agent_runner is None:
                raise RuntimeError("P0 event but no agent_runner wired")
            report_path = agent_runner(evt, portfolio, out_dir, classification)
            mark_processed(db_conn, evt.event_id, now)
            record_decision(
                db_conn,
                "interrupt_P0",
                event=evt,
                severity=sev,
                rationale=classification.rationale,
                report_path=report_path,
            )
            report.decisions.append(
                EventDecision(
                    event_id=evt.event_id,
                    cycle_type="interrupt_P0",
                    severity=sev,
                    rationale=classification.rationale,
                    report_path=report_path,
                )
            )
            logger.info("interrupt_P0 event_id=%s report=%s", evt.event_id, report_path)
        elif sev in ("P1", "P2"):
            cycle = f"deferred_{sev}"
            # P1/P2 are still "processed" enough to update cooldown — prevents
            # the same noise re-entering the deferred journal repeatedly.
            mark_processed(db_conn, evt.event_id, now)
            record_decision(
                db_conn,
                cycle,
                event=evt,
                severity=sev,
                rationale=classification.rationale,
            )
            report.decisions.append(
                EventDecision(
                    event_id=evt.event_id,
                    cycle_type=cycle,
                    severity=sev,
                    rationale=classification.rationale,
                )
            )
            logger.info("%s event_id=%s", cycle, evt.event_id)
        else:  # pragma: no cover — defensive, classify_severity already validates
            raise ValueError(f"unexpected severity: {sev!r}")

    return report
