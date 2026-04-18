"""Severity classifier unit tests.

The session prompt asked for VCR; in this overnight run no ANTHROPIC_API_KEY
is available so the live recording step can't run. Replay-mode fixtures
(``tests/fixtures/replay/events/classify/<event_id>.json``) double as the
deterministic backing data for these tests, with a separate stub-client
test demonstrating the live parse path.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from ria.agent.event import Event
from ria.models import Portfolio, Position
from ria.tools.classify import (
    MAX_INPUT_CHARS,
    ClassifierResult,
    build_user_prompt,
    classify_severity,
    parse_response_text,
)

EVENTS_DIR = Path(__file__).parent / "fixtures" / "synthetic_events"
CLASSIFY_REPLAY = Path(__file__).parent / "fixtures" / "replay" / "events" / "classify"


def _portfolio() -> Portfolio:
    return Portfolio(
        positions=[
            Position(ticker="TSLA", quantity=30, cost_basis_usd=8400),
            Position(ticker="AAPL", quantity=15, cost_basis_usd=3500),
            Position(ticker="NVDA", quantity=3, cost_basis_usd=2100),
        ],
        cash_usd=500.0,
    )


# ---- prompt construction ---------------------------------------------------

def test_build_user_prompt_includes_holdings_and_event_text():
    pf = _portfolio()
    evt = Event.from_path(EVENTS_DIR / "evt_tsla_earnings_miss.json")
    msg = build_user_prompt(evt, pf)
    assert "TSLA" in msg
    assert "AAPL" in msg
    assert "Tesla Q1 2026 EPS" in msg
    assert evt.event_id in msg


def test_build_user_prompt_truncates_long_text():
    pf = _portfolio()
    long = "x" * (MAX_INPUT_CHARS + 1000)
    evt = Event(
        event_id="evt_long",
        ts_utc="2026-04-15T20:00:00Z",
        source_type="news",
        raw_text=long,
    )
    msg = build_user_prompt(evt, pf)
    # ensures the truncation marker is present and total length within budget+headers
    assert "[truncated]" in msg
    raw_section = msg.split("---\n", 1)[1]
    raw_section = raw_section.split("\n---", 1)[0]
    assert len(raw_section) <= MAX_INPUT_CHARS + len("...[truncated]") + 5


# ---- parser ---------------------------------------------------------------

def test_parse_response_plain_json():
    out = parse_response_text('{"severity": "P0", "rationale": "TSLA direct hit"}')
    assert out.severity == "P0"
    assert "direct" in out.rationale.lower()


def test_parse_response_with_fences():
    text = '```json\n{"severity": "P2", "rationale": "noise"}\n```'
    out = parse_response_text(text)
    assert out.severity == "P2"


def test_parse_response_invalid_severity():
    with pytest.raises(ValueError, match="invalid severity"):
        parse_response_text('{"severity": "P9", "rationale": "x"}')


def test_parse_response_missing_rationale_defaults():
    out = parse_response_text('{"severity": "P1"}')
    assert out.severity == "P1"
    assert out.rationale == "(no rationale)"


# ---- replay mode ----------------------------------------------------------

def test_classify_replay_p0():
    pf = _portfolio()
    evt = Event.from_path(EVENTS_DIR / "evt_tsla_earnings_miss.json")
    out = classify_severity(evt, pf, replay_dir=CLASSIFY_REPLAY)
    assert out.severity == "P0"
    assert "TSLA" in out.rationale or "Tesla" in out.rationale


def test_classify_replay_p2():
    pf = _portfolio()
    evt = Event.from_path(EVENTS_DIR / "evt_random_fintwit_noise.json")
    out = classify_severity(evt, pf, replay_dir=CLASSIFY_REPLAY)
    assert out.severity == "P2"


def test_classify_replay_dup_uses_same_fixture_as_original():
    """DUP shares the same event_id as the TSLA earnings event, so the
    replay lookup must surface the same response."""
    pf = _portfolio()
    evt = Event.from_path(EVENTS_DIR / "evt_tsla_earnings_miss_DUP.json")
    out = classify_severity(evt, pf, replay_dir=CLASSIFY_REPLAY)
    assert out.severity == "P0"


def test_classify_replay_missing_fixture_raises(tmp_path):
    pf = _portfolio()
    evt = Event(
        event_id="evt_missing",
        ts_utc="2026-04-15T20:00:00Z",
        source_type="news",
        raw_text="x",
    )
    with pytest.raises(FileNotFoundError):
        classify_severity(evt, pf, replay_dir=tmp_path)


# ---- live path with stub client -------------------------------------------

class _StubBlock:
    def __init__(self, text: str):
        self.type = "text"
        self.text = text


class _StubResp:
    def __init__(self, text: str):
        self.content = [_StubBlock(text)]


class _StubMessages:
    def __init__(self, text: str):
        self._text = text
        self.calls: list[dict] = []

    def create(self, **kw):
        self.calls.append(kw)
        return _StubResp(self._text)


class _StubClient:
    def __init__(self, text: str):
        self.messages = _StubMessages(text)


def test_classify_live_path_uses_injected_client():
    pf = _portfolio()
    evt = Event.from_path(EVENTS_DIR / "evt_tsla_earnings_miss.json")
    client = _StubClient('{"severity": "P0", "rationale": "stub"}')
    out = classify_severity(evt, pf, client=client)
    assert out.severity == "P0"
    assert client.messages.calls[0]["model"].startswith("claude-haiku")
    assert "max_tokens" in client.messages.calls[0]
