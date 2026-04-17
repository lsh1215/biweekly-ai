"""Agent-loop TDD — 3 stages.

Stage 1 (this file, mock-based): verifies tool schemas, dispatcher, and replay
semantics with injected fake tools. No network, no DB, no real fixtures.

Stage 2 (recording): ``tests/fixtures/replay/healthcheck.json`` is a canonical
messages-API exchange captured for replay. When ``ANTHROPIC_API_KEY`` is
absent the fixture is hand-authored (documented in the ``_note`` field);
otherwise Sprint 2 re-records it with a live Opus 4.7 call.

Stage 3 (replay integration): ``test_replay_fixture_end_to_end_smoke`` loads
the committed fixture and exercises the full loop against real tool impls
(with emit_report redirected to a tmp dir).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ria.agent.loop import (
    MAX_ITERATIONS,
    TOOL_NAMES,
    TOOL_SCHEMAS,
    LoopResult,
    dispatch_tool,
    run_agent,
)


# ---- Stage 1: schemas + dispatcher -----------------------------------------

def test_tool_schemas_cover_required_set():
    assert TOOL_NAMES == {"get_prices", "get_news", "rag_search", "emit_report"}
    for t in TOOL_SCHEMAS:
        assert "name" in t
        assert "description" in t
        assert "input_schema" in t
        assert t["input_schema"]["type"] == "object"


def test_max_iterations_is_15():
    assert MAX_ITERATIONS == 15


def test_dispatch_tool_routes_by_name():
    calls: list[tuple] = []
    tools = {
        "get_prices": lambda tickers, window_days: (
            calls.append(("p", tickers, window_days)) or [{"ticker": tickers[0]}]
        ),
        "get_news": lambda ticker, last_n_days: (
            calls.append(("n", ticker, last_n_days)) or []
        ),
    }
    result = dispatch_tool("get_prices", {"tickers": ["AAPL"], "window_days": 5}, tools)
    assert result == [{"ticker": "AAPL"}]
    assert calls == [("p", ["AAPL"], 5)]


def test_dispatch_tool_unknown_raises():
    with pytest.raises(ValueError, match="unknown tool"):
        dispatch_tool("nonexistent", {}, {})


def test_dispatch_tool_arg_errors_propagate():
    def bad_tool(**kw):
        raise RuntimeError("tool blew up")

    with pytest.raises(RuntimeError, match="tool blew up"):
        dispatch_tool("x", {"a": 1}, {"x": bad_tool})


# ---- Stage 1: replay semantics with injected fakes -------------------------

def _synthetic_turns(ticker_summary: str = "aapl_tsla_nvda") -> list[dict]:
    return [
        {
            "assistant": {
                "id": "msg_01",
                "stop_reason": "tool_use",
                "content": [
                    {"type": "text", "text": "가격부터 확인."},
                    {
                        "type": "tool_use",
                        "id": "tu_1",
                        "name": "get_prices",
                        "input": {"tickers": ["AAPL"], "window_days": 3},
                    },
                ],
            }
        },
        {
            "assistant": {
                "id": "msg_02",
                "stop_reason": "tool_use",
                "content": [
                    {"type": "text", "text": "HOLD 결정."},
                    {
                        "type": "tool_use",
                        "id": "tu_2",
                        "name": "emit_report",
                        "input": {
                            "title": "HOLD weekly",
                            "sections": [{"heading": "Summary", "body": "HOLD 유지"}],
                            "citations": [
                                "https://x.example/a",
                                "https://y.example/b",
                            ],
                            "ticker_summary": ticker_summary,
                        },
                    },
                ],
            }
        },
        {
            "assistant": {
                "id": "msg_03",
                "stop_reason": "end_turn",
                "content": [{"type": "text", "text": "완료."}],
            }
        },
    ]


def test_replay_mode_dispatches_tools_and_captures_report(tmp_path):
    fixture = {
        "_note": "unit-test synthetic",
        "system": "sys",
        "user": "user",
        "turns": _synthetic_turns(),
    }
    fp = tmp_path / "replay.json"
    fp.write_text(json.dumps(fixture))

    tool_calls: list[tuple] = []

    def fake_prices(tickers, window_days):
        tool_calls.append(("p", tickers, window_days))
        return [{"ticker": tickers[0], "Close": 150.0}]

    def fake_emit(**kw):
        out = tmp_path / "planned_20260413_aapl_tsla_nvda.md"
        body = f"# {kw['title']}\n\n"
        for s in kw["sections"]:
            body += f"## {s['heading']}\n\n{s['body']}\n\n"
        body += "## Citations\n\n"
        for c in kw["citations"]:
            body += f"- {c}\n"
        out.write_text(body)
        return str(out)

    tools = {
        "get_prices": fake_prices,
        "get_news": lambda ticker, last_n_days: [],
        "rag_search": lambda query, top_k=5: [],
        "emit_report": fake_emit,
    }

    result = run_agent("sys", "user", replay_path=fp, tools=tools)
    assert isinstance(result, LoopResult)
    assert result.replay is True
    assert result.turns == 3
    assert result.report_path is not None
    assert Path(result.report_path).exists()
    names = [c["name"] for c in result.tool_calls]
    assert names == ["get_prices", "emit_report"]
    assert tool_calls[0] == ("p", ["AAPL"], 3)


def test_replay_determinism_same_input_same_output(tmp_path):
    fixture = {"turns": _synthetic_turns()}
    fp = tmp_path / "replay.json"
    fp.write_text(json.dumps(fixture))

    def fake_emit(**kw):
        out = tmp_path / "planned_20260413_aapl_tsla_nvda.md"
        body = "# " + kw["title"] + "\n" + "\n".join(f"- {c}" for c in kw["citations"])
        out.write_text(body)
        return str(out)

    tools = {
        "get_prices": lambda tickers, window_days: [],
        "get_news": lambda ticker, last_n_days: [],
        "rag_search": lambda query, top_k=5: [],
        "emit_report": fake_emit,
    }

    r1 = run_agent("s", "u", replay_path=fp, tools=tools)
    content1 = Path(r1.report_path).read_text()
    # re-run
    r2 = run_agent("s", "u", replay_path=fp, tools=tools)
    content2 = Path(r2.report_path).read_text()
    assert content1 == content2
    assert r1.turns == r2.turns
    assert [c["name"] for c in r1.tool_calls] == [c["name"] for c in r2.tool_calls]


def test_replay_missing_file_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        run_agent("s", "u", replay_path=tmp_path / "nope.json")


def test_replay_passes_on_empty_text_turns(tmp_path):
    fixture = {
        "turns": [
            {
                "assistant": {
                    "stop_reason": "end_turn",
                    "content": [{"type": "text", "text": "nothing to do"}],
                }
            }
        ]
    }
    fp = tmp_path / "r.json"
    fp.write_text(json.dumps(fixture))
    tools = {"get_prices": lambda **k: [], "get_news": lambda **k: [],
             "rag_search": lambda **k: [], "emit_report": lambda **k: ""}
    result = run_agent("s", "u", replay_path=fp, tools=tools)
    assert result.turns == 1
    assert result.report_path is None


# ---- Stage 3: committed fixture end-to-end smoke ---------------------------

REPLAY_FIXTURE = Path(__file__).parent / "fixtures" / "replay" / "healthcheck.json"


@pytest.mark.skipif(
    not REPLAY_FIXTURE.exists(),
    reason="healthcheck replay fixture not yet recorded",
)
def test_replay_fixture_end_to_end_smoke(tmp_path, monkeypatch):
    """Load the committed fixture and run through the loop with a wrapped
    emit_report that writes into tmp_path. Verifies citation + verb gates."""
    from ria.tools.emit_report import emit_report as real_emit
    from datetime import date

    def _emit(**kw):
        kw.pop("out_dir", None)
        kw.pop("as_of", None)
        path = real_emit(out_dir=tmp_path, as_of=date(2026, 4, 13), **kw)
        return str(path)

    tools = {
        "get_prices": lambda **kw: [],
        "get_news": lambda **kw: [],
        "rag_search": lambda **kw: [],
        "emit_report": _emit,
    }

    result = run_agent("sys", "user", replay_path=REPLAY_FIXTURE, tools=tools)
    assert result.report_path is not None
    text = Path(result.report_path).read_text()
    from ria.tools.emit_report import ACTION_VERBS

    head = text[:200].upper()
    assert any(v in head for v in ACTION_VERBS), (
        f"no action verb in first 200 chars: {head!r}"
    )
    # citation minimum
    cite_lines = sum(
        1 for ln in text.splitlines()
        if ("http://" in ln or "https://" in ln or "accession" in ln.lower())
        and ln.strip().startswith("-")
    )
    assert cite_lines >= 2
