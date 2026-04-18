"""Event off-cycle loop unit tests.

Pure-Python: severity gate + cooldown + clock injection. Anthropic + agent
loop are mocked so this file runs without an API key and without the agent
loop module's tool fixtures.

Postgres is used directly (Docker compose container is up during overnight
runs and CI). Each test creates a unique event_id namespace and rolls back
its rows in teardown to keep parallel runs safe.
"""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path

import pytest

from ria.agent.event import Event
from ria.agent.event_loop import EventDecision, load_events, process_all
from ria.journal import mark_processed, record_decision, within_cooldown
from ria.models import Portfolio, Position
from ria.tools.classify import ClassifierResult


pytestmark = pytest.mark.skipif(
    os.environ.get("RIA_SKIP_DB_TESTS") == "1",
    reason="DB-dependent tests skipped via RIA_SKIP_DB_TESTS=1",
)


def _portfolio() -> Portfolio:
    return Portfolio(
        positions=[
            Position(ticker="TSLA", quantity=30, cost_basis_usd=8400),
            Position(ticker="AAPL", quantity=15, cost_basis_usd=3500),
            Position(ticker="NVDA", quantity=3, cost_basis_usd=2100),
        ],
        cash_usd=500.0,
    )


@pytest.fixture
def conn():
    """Live Postgres connection with schema ensured. Cleans up its own rows."""
    psycopg = pytest.importorskip("psycopg")
    from ria.db.conn import connect, ensure_schema

    try:
        c = connect()
    except psycopg.OperationalError as e:
        pytest.skip(f"Postgres unavailable: {e}")
    ensure_schema(c)
    namespace = f"test_{uuid.uuid4().hex[:8]}"
    yield c, namespace
    with c.cursor() as cur:
        cur.execute("DELETE FROM decisions WHERE event_id LIKE %s", (f"{namespace}%",))
        cur.execute("DELETE FROM event_cooldown WHERE event_id LIKE %s", (f"{namespace}%",))
    c.commit()
    c.close()


def _make_event(ns: str, suffix: str, ts: str, *, ticker: str = "TSLA") -> Event:
    return Event(
        event_id=f"{ns}_{suffix}",
        ts_utc=ts,
        source_type="earnings_report",
        raw_text="synthetic",
        expected_affected_tickers=[ticker],
    )


def _write_events(tmp_path: Path, events: list[Event]) -> Path:
    qdir = tmp_path / "queue"
    qdir.mkdir()
    for evt in events:
        fp = qdir / f"{evt.event_id}.json"
        # Pydantic v2: dump excluding None defaults
        fp.write_text(evt.model_dump_json(indent=2))
    return qdir


# ---- load_events ordering --------------------------------------------------

def test_load_events_sorts_by_ts_utc_ascending(tmp_path):
    a = _make_event("ns_a", "1", "2026-04-15T22:00:00Z")
    b = _make_event("ns_a", "2", "2026-04-15T20:00:00Z")
    c = _make_event("ns_a", "3", "2026-04-16T09:30:00Z")
    qdir = _write_events(tmp_path, [a, b, c])
    out = load_events(qdir)
    assert [e.event_id for e in out] == ["ns_a_2", "ns_a_1", "ns_a_3"]


# ---- severity gate (P0 vs P1 vs P2) ----------------------------------------

def test_p0_triggers_interrupt_and_journals(tmp_path, conn):
    c, ns = conn
    evt = _make_event(ns, "p0", "2026-04-15T20:00:00Z")
    qdir = _write_events(tmp_path, [evt])

    captured: dict[str, object] = {}

    def fake_classify(e, pf):
        return ClassifierResult(severity="P0", rationale="direct hit")

    def fake_runner(e, pf, out_dir, classification):
        rp = out_dir / f"interrupt_P0_20260415_{e.expected_affected_tickers[0]}.md"
        rp.write_text("# REVIEW interrupt\n")
        captured["called"] = True
        return rp

    out_dir = tmp_path / "reports"
    fixed_now = datetime(2026, 4, 15, 20, 5, 0)
    report = process_all(
        qdir,
        _portfolio(),
        out_dir,
        db_conn=c,
        now_fn=lambda: fixed_now,
        classify_fn=fake_classify,
        agent_runner=fake_runner,
    )

    assert captured.get("called") is True
    assert len(report.by_cycle("interrupt_P0")) == 1
    # journal row written
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type FROM decisions WHERE event_id=%s ORDER BY id", (evt.event_id,)
        )
        rows = [r[0] for r in cur.fetchall()]
    assert rows == ["interrupt_P0"]


def test_p1_does_not_trigger_interrupt_journals_deferred(tmp_path, conn):
    c, ns = conn
    evt = _make_event(ns, "p1", "2026-04-15T20:00:00Z")
    qdir = _write_events(tmp_path, [evt])

    runner_called: list[bool] = []

    def fake_classify(e, pf):
        return ClassifierResult(severity="P1", rationale="sector macro")

    def fake_runner(*a, **k):
        runner_called.append(True)
        return None

    report = process_all(
        qdir,
        _portfolio(),
        tmp_path / "reports",
        db_conn=c,
        now_fn=lambda: datetime(2026, 4, 15, 20, 5),
        classify_fn=fake_classify,
        agent_runner=fake_runner,
    )

    assert runner_called == []
    assert len(report.by_cycle("interrupt_P0")) == 0
    assert len(report.by_cycle("deferred_P1")) == 1
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type FROM decisions WHERE event_id=%s ORDER BY id", (evt.event_id,)
        )
        rows = [r[0] for r in cur.fetchall()]
    assert rows == ["deferred_P1"]


def test_p2_does_not_trigger_interrupt_journals_deferred(tmp_path, conn):
    c, ns = conn
    evt = _make_event(ns, "p2", "2026-04-16T09:30:00Z")
    qdir = _write_events(tmp_path, [evt])

    def fake_classify(e, pf):
        return ClassifierResult(severity="P2", rationale="noise")

    report = process_all(
        qdir,
        _portfolio(),
        tmp_path / "reports",
        db_conn=c,
        now_fn=lambda: datetime(2026, 4, 16, 9, 35),
        classify_fn=fake_classify,
        agent_runner=lambda *a, **k: None,
    )

    assert len(report.by_cycle("interrupt_P0")) == 0
    assert len(report.by_cycle("deferred_P2")) == 1


# ---- cooldown + clock injection -------------------------------------------

def test_dup_inside_cooldown_window_is_skipped(tmp_path, conn):
    """Process the same event_id twice within 23h — second is cooldown_skip."""
    c, ns = conn
    evt = _make_event(ns, "dup", "2026-04-15T20:00:00Z")
    qdir = _write_events(tmp_path, [evt])

    def fake_classify(e, pf):
        return ClassifierResult(severity="P0", rationale="direct hit")

    rp = tmp_path / "rep.md"
    rp.write_text("x")

    runs: list[str] = []

    def fake_runner(e, pf, out_dir, classification):
        runs.append(e.event_id)
        return rp

    # 1st run at t0
    t0 = datetime(2026, 4, 15, 20, 5)
    process_all(
        qdir, _portfolio(), tmp_path / "out",
        db_conn=c, now_fn=lambda: t0,
        classify_fn=fake_classify, agent_runner=fake_runner,
    )

    # 2nd run at t0 + 23h (still within 24h window)
    t1 = t0 + timedelta(hours=23)
    process_all(
        qdir, _portfolio(), tmp_path / "out",
        db_conn=c, now_fn=lambda: t1,
        classify_fn=fake_classify, agent_runner=fake_runner,
    )

    # runner only fired once — second call should have been short-circuited
    assert runs == [evt.event_id]
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type FROM decisions WHERE event_id=%s ORDER BY id", (evt.event_id,)
        )
        rows = [r[0] for r in cur.fetchall()]
    assert rows == ["interrupt_P0", "cooldown_skip"]


def test_dup_after_cooldown_expires_reprocesses(tmp_path, conn):
    """Same event_id at t0 + 25h must reprocess (cooldown lapsed)."""
    c, ns = conn
    evt = _make_event(ns, "post_cd", "2026-04-15T20:00:00Z")
    qdir = _write_events(tmp_path, [evt])

    runs: list[str] = []

    def fake_classify(e, pf):
        return ClassifierResult(severity="P0", rationale="direct hit")

    def fake_runner(e, pf, out_dir, classification):
        runs.append(e.event_id)
        return tmp_path / f"r_{len(runs)}.md"

    t0 = datetime(2026, 4, 15, 20, 5)
    process_all(
        qdir, _portfolio(), tmp_path / "out",
        db_conn=c, now_fn=lambda: t0,
        classify_fn=fake_classify, agent_runner=fake_runner,
    )
    t1 = t0 + timedelta(hours=25)
    process_all(
        qdir, _portfolio(), tmp_path / "out",
        db_conn=c, now_fn=lambda: t1,
        classify_fn=fake_classify, agent_runner=fake_runner,
    )

    assert runs == [evt.event_id, evt.event_id]
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type FROM decisions WHERE event_id=%s ORDER BY id", (evt.event_id,)
        )
        rows = [r[0] for r in cur.fetchall()]
    assert rows == ["interrupt_P0", "interrupt_P0"]


# ---- single-batch ordering: P0 then DUP-in-batch is skipped ---------------

def test_single_batch_processes_unique_then_skips_duplicate(tmp_path, conn):
    """The checkpoint scenario: one queue contains P0 + DUP + P2.
    Process them in ts_utc order; DUP must short-circuit on cooldown."""
    c, ns = conn
    p0 = _make_event(ns, "p0", "2026-04-15T20:00:00Z")
    dup = Event(
        event_id=p0.event_id,  # exact duplicate id
        ts_utc="2026-04-15T22:00:00Z",
        source_type="earnings_report",
        raw_text="dup body",
        expected_affected_tickers=["TSLA"],
    )
    p2 = _make_event(ns, "p2", "2026-04-16T09:30:00Z", ticker="AAPL")
    # Sort tag the dup so glob picks it as a separate file
    qdir = tmp_path / "queue"
    qdir.mkdir()
    (qdir / f"{p0.event_id}.json").write_text(p0.model_dump_json())
    (qdir / f"{p0.event_id}__DUP.json").write_text(dup.model_dump_json())
    (qdir / f"{p2.event_id}.json").write_text(p2.model_dump_json())

    def fake_classify(e, pf):
        if e.event_id.endswith("_p2"):
            return ClassifierResult(severity="P2", rationale="noise")
        return ClassifierResult(severity="P0", rationale="direct hit")

    runs: list[str] = []

    def fake_runner(e, pf, out_dir, classification):
        runs.append(e.event_id)
        return tmp_path / f"r_{len(runs)}.md"

    report = process_all(
        qdir, _portfolio(), tmp_path / "out",
        db_conn=c, now_fn=lambda: datetime(2026, 4, 16, 10, 0),
        classify_fn=fake_classify, agent_runner=fake_runner,
    )

    cycles = [d.cycle_type for d in report.decisions]
    # P0 first (earliest ts_utc), DUP cooldown_skip, P2 deferred
    assert cycles == ["interrupt_P0", "cooldown_skip", "deferred_P2"]
    assert runs == [p0.event_id]


# ---- low-level cooldown helpers -------------------------------------------

def test_within_cooldown_false_when_no_record(conn):
    c, ns = conn
    assert within_cooldown(c, f"{ns}_never", datetime(2026, 4, 15)) is False


def test_within_cooldown_true_inside_window(conn):
    c, ns = conn
    eid = f"{ns}_marked"
    t0 = datetime(2026, 4, 15, 0, 0)
    mark_processed(c, eid, t0)
    assert within_cooldown(c, eid, t0 + timedelta(hours=23)) is True


def test_within_cooldown_false_outside_window(conn):
    c, ns = conn
    eid = f"{ns}_lapsed"
    t0 = datetime(2026, 4, 15, 0, 0)
    mark_processed(c, eid, t0)
    assert within_cooldown(c, eid, t0 + timedelta(hours=25)) is False


def test_record_decision_persists_row(conn):
    c, ns = conn
    eid = f"{ns}_dec"
    evt = _make_event(ns, "dec", "2026-04-15T20:00:00Z")
    record_decision(
        c, "deferred_P1", event=evt, severity="P1", rationale="macro"
    )
    with c.cursor() as cur:
        cur.execute(
            "SELECT cycle_type, severity, rationale FROM decisions WHERE event_id=%s",
            (evt.event_id,),
        )
        row = cur.fetchone()
    assert row == ("deferred_P1", "P1", "macro")
