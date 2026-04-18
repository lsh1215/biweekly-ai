"""Cost tracker unit tests (Sprint 4).

Pure-Python: pricing math + JSONL ledger + strict summary file writer.
No DB, no Anthropic, no fixtures dependency. Runs from a tmp_path.

The summary format is a **contract** with VERIFY.sh — first line must match
``awk 'NR==1 && /^total \\$[0-9]+\\.[0-9]+/'`` so the verifier can extract
the total. Regression here would break the Sprint 0 cost_probe parser.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from ria.cost_tracker import (
    BUDGET_USD_HARD,
    compute_usd,
    load_ledger,
    record,
    write_summary,
)


# ---- pricing math ---------------------------------------------------------

def test_compute_usd_opus_rate():
    # 1M input tokens at $15 + 1M output at $75 = $90
    assert compute_usd("claude-opus-4-7", 1_000_000, 1_000_000) == pytest.approx(90.0, rel=1e-9)


def test_compute_usd_haiku_rate():
    # 1M input at $1 + 1M output at $5 = $6
    assert compute_usd("claude-haiku-4-5", 1_000_000, 1_000_000) == pytest.approx(6.0, rel=1e-9)


def test_compute_usd_small_call_opus():
    # 3214 input + 892 output Opus call (sample from session spec)
    v = compute_usd("claude-opus-4-7", 3214, 892)
    # 3214*15/1e6 + 892*75/1e6 = 0.04821 + 0.0669 = 0.11511
    assert v == pytest.approx(0.11511, abs=1e-6)


def test_compute_usd_unknown_model_raises():
    with pytest.raises(ValueError, match="unknown model"):
        compute_usd("not-a-model", 10, 10)


def test_compute_usd_zero_tokens():
    assert compute_usd("claude-opus-4-7", 0, 0) == 0.0


# ---- ledger I/O -----------------------------------------------------------

def test_record_appends_jsonl_entry(tmp_path):
    ledger = tmp_path / "cost_ledger.jsonl"
    record("planned_20260417", "claude-opus-4-7", 3214, 892, ledger_path=ledger)
    assert ledger.exists()
    lines = ledger.read_text().splitlines()
    assert len(lines) == 1
    row = json.loads(lines[0])
    assert row["label"] == "planned_20260417"
    assert row["model"] == "claude-opus-4-7"
    assert row["input_tokens"] == 3214
    assert row["output_tokens"] == 892


def test_record_multiple_appends(tmp_path):
    ledger = tmp_path / "cost_ledger.jsonl"
    record("a", "claude-opus-4-7", 100, 50, ledger_path=ledger)
    record("b", "claude-haiku-4-5", 200, 30, ledger_path=ledger)
    rows = load_ledger(ledger)
    assert [r["label"] for r in rows] == ["a", "b"]


def test_load_ledger_missing_returns_empty(tmp_path):
    assert load_ledger(tmp_path / "nope.jsonl") == []


# ---- summary writer — strict VERIFY.sh contract ---------------------------

VERIFY_TOTAL_RE = re.compile(r"^total \$[0-9]+\.[0-9]+$")


def test_write_summary_first_line_strict_match(tmp_path):
    ledger = tmp_path / "cost_ledger.jsonl"
    record("planned_20260417", "claude-opus-4-7", 3214, 892, ledger_path=ledger)
    record("classify_evt_x", "claude-haiku-4-5", 512, 68, ledger_path=ledger)

    summary = tmp_path / "cost_summary.md"
    write_summary(ledger, summary)

    first_line = summary.read_text().splitlines()[0]
    assert VERIFY_TOTAL_RE.match(first_line), (
        f"first line must match `total $X.XX` literal, got: {first_line!r}"
    )


def test_write_summary_per_call_lines_format(tmp_path):
    ledger = tmp_path / "cost_ledger.jsonl"
    record("planned_20260413", "claude-opus-4-7", 3214, 892, ledger_path=ledger)
    record("interrupt_P0_20260415_TSLA", "claude-opus-4-7", 2891, 720, ledger_path=ledger)
    record("classify_evt_tsla_earnings_miss", "claude-haiku-4-5", 512, 68, ledger_path=ledger)

    summary = tmp_path / "cost_summary.md"
    write_summary(ledger, summary)

    lines = summary.read_text().splitlines()
    # first line total, then three per-call entries
    assert VERIFY_TOTAL_RE.match(lines[0])
    assert len(lines) >= 4
    # each detail line: <label>: input=<N> output=<N> usd=<N.NNNN>
    detail_re = re.compile(
        r"^[A-Za-z0-9_]+: input=\d+ output=\d+ usd=\d+\.\d{4}$"
    )
    for line in lines[1:4]:
        assert detail_re.match(line), f"bad detail line: {line!r}"


def test_write_summary_total_equals_sum_of_entries(tmp_path):
    ledger = tmp_path / "cost_ledger.jsonl"
    record("a", "claude-opus-4-7", 10_000, 5_000, ledger_path=ledger)
    record("b", "claude-haiku-4-5", 10_000, 5_000, ledger_path=ledger)

    summary = tmp_path / "cost_summary.md"
    write_summary(ledger, summary)

    first = summary.read_text().splitlines()[0]
    m = re.match(r"^total \$([0-9]+\.[0-9]+)$", first)
    assert m is not None
    total = float(m.group(1))
    # Opus: 10000*15/1e6 + 5000*75/1e6 = 0.15 + 0.375 = 0.525
    # Haiku: 10000*1/1e6 + 5000*5/1e6 = 0.01 + 0.025 = 0.035
    assert total == pytest.approx(0.56, abs=0.01)


def test_write_summary_over_hard_budget_raises(tmp_path):
    """Total > $50 → write_summary raises RuntimeError (checkpoint fail)."""
    ledger = tmp_path / "cost_ledger.jsonl"
    # Force a > $50 total with Opus output tokens (cheapest to blow the budget by mass)
    # 800000 output * 75/1e6 = $60
    record("big", "claude-opus-4-7", 0, 800_000, ledger_path=ledger)

    summary = tmp_path / "cost_summary.md"
    with pytest.raises(RuntimeError, match="cost budget"):
        write_summary(ledger, summary)
    # summary file is still written (so the user sees the breakdown on fail)
    assert summary.exists()
    assert summary.read_text().startswith("total $")


def test_write_summary_empty_ledger_emits_zero_total(tmp_path):
    ledger = tmp_path / "cost_ledger.jsonl"
    ledger.write_text("")
    summary = tmp_path / "cost_summary.md"
    write_summary(ledger, summary)
    first = summary.read_text().splitlines()[0]
    assert VERIFY_TOTAL_RE.match(first)
    m = re.match(r"^total \$([0-9]+\.[0-9]+)$", first)
    assert float(m.group(1)) == 0.0


def test_write_summary_idempotent_overwrite(tmp_path):
    """Calling write_summary twice yields the same content — no appending."""
    ledger = tmp_path / "cost_ledger.jsonl"
    record("a", "claude-opus-4-7", 100, 50, ledger_path=ledger)
    summary = tmp_path / "cost_summary.md"
    write_summary(ledger, summary)
    first = summary.read_text()
    write_summary(ledger, summary)
    second = summary.read_text()
    assert first == second


# ---- budget constant is $50 per PRD --------------------------------------

def test_budget_constant_is_fifty_usd():
    assert BUDGET_USD_HARD == 50.0
