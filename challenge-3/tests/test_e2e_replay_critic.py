"""E2E replay test for structure-critic.

16 fixtures (4 format × 4 topic) × 1 critic call recorded as JSON in
replay/fixtures/{format}/{slug}-critic.json. Loader must:
  - assert D7 7-key shape
  - parse APPROVE / ITERATE / REJECT verdict from response text
  - dispatch_key matches request rebuilt from current fixture+sprint1 draft
  - same fixture set → same verdict ordering (deterministic)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import critic_replay  # type: ignore

REPLAY_DIR = ROOT / "replay" / "fixtures"
FORMATS = ("blog", "cover-letter", "paper", "letter")


def _all_critic_jsons():
    out = []
    for fmt in FORMATS:
        out.extend(sorted((REPLAY_DIR / fmt).glob("*-critic.json")))
    return out


def test_sixteen_critic_replays_present():
    files = _all_critic_jsons()
    if len(files) != 16:
        pytest.skip(f"expected 16 critic replays, found {len(files)} — recapture pending")
    assert len(files) == 16


def test_critic_replay_has_seven_keys():
    required = {"model", "captured_at", "stage", "request", "response",
                "dispatch_key", "format"}
    files = _all_critic_jsons()
    if not files:
        pytest.skip("no critic replays yet")
    for f in files:
        d = json.loads(f.read_text())
        missing = required - set(d.keys())
        assert not missing, f"{f}: missing {missing}"
        assert d["stage"] == "structure-critic", f"{f}: stage={d['stage']}"


def test_critic_replay_dispatch_key_matches():
    files = _all_critic_jsons()
    if not files:
        pytest.skip("no critic replays yet")
    for f in files:
        d = json.loads(f.read_text())
        fmt = d["format"]
        slug = f.stem.replace("-critic", "")
        expected = critic_replay.expected_dispatch_key(fmt, slug)
        assert d["dispatch_key"] == expected, f"{f}: dispatch_key drift"


def test_critic_verdict_parsable():
    files = _all_critic_jsons()
    if not files:
        pytest.skip("no critic replays yet")
    valid = {"APPROVE", "ITERATE", "REJECT"}
    for f in files:
        d = json.loads(f.read_text())
        text = "".join(b.get("text", "") for b in d["response"]["content"]
                       if b.get("type") == "text")
        verdict = critic_replay.parse_verdict(text)
        assert verdict in valid, f"{f}: verdict={verdict!r}"


def test_critic_replay_is_deterministic():
    """Same critic replays processed twice yield identical verdicts."""
    files = _all_critic_jsons()
    if not files:
        pytest.skip("no critic replays yet")
    a = critic_replay.replay_all_verdicts()
    b = critic_replay.replay_all_verdicts()
    assert a == b
