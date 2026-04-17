"""emit_report unit tests — TDD step 1 (test before implementation)."""

from __future__ import annotations

from datetime import date

import pytest

from ria.tools.emit_report import ACTION_VERBS, emit_report


def test_zero_citations_raises(tmp_path):
    with pytest.raises(ValueError, match="citation"):
        emit_report(
            title="HOLD test",
            sections=[{"heading": "Summary", "body": "body"}],
            citations=[],
            out_dir=tmp_path,
        )


def test_single_citation_raises(tmp_path):
    with pytest.raises(ValueError, match="citation"):
        emit_report(
            title="HOLD test",
            sections=[{"heading": "Summary", "body": "body"}],
            citations=["https://only-one.example.com/a"],
            out_dir=tmp_path,
        )


def test_planned_filename_format(tmp_path):
    path = emit_report(
        title="HOLD weekly health",
        sections=[{"heading": "Summary", "body": "HOLD 유지"}],
        citations=["https://a.example/x", "https://b.example/y"],
        kind="planned",
        as_of=date(2026, 4, 13),
        ticker_summary="aapl_tsla_nvda",
        out_dir=tmp_path,
    )
    assert path.name == "planned_20260413_aapl_tsla_nvda.md"
    assert path.exists()


def test_interrupt_filename_format(tmp_path):
    path = emit_report(
        title="REVIEW TSLA earnings miss",
        sections=[{"heading": "Alert", "body": "REVIEW 필요"}],
        citations=[
            "https://news.example/tsla-miss",
            "accession:0001318605-25-000001",
        ],
        kind="interrupt",
        severity="P0",
        as_of=date(2026, 4, 15),
        ticker="TSLA",
        out_dir=tmp_path,
    )
    assert path.name == "interrupt_P0_20260415_TSLA.md"


def test_interrupt_requires_severity_and_ticker(tmp_path):
    with pytest.raises(ValueError):
        emit_report(
            title="REVIEW",
            sections=[{"heading": "x", "body": "y"}],
            citations=["https://a", "https://b"],
            kind="interrupt",
            as_of=date(2026, 4, 15),
            out_dir=tmp_path,
        )


def test_markdown_contains_title_sections_and_citations_block(tmp_path):
    path = emit_report(
        title="HOLD weekly snapshot",
        sections=[
            {"heading": "Summary", "body": "HOLD 권고. 리스크 관리 양호."},
            {"heading": "상세", "body": "AAPL +1.2%, TSLA -0.5%"},
        ],
        citations=[
            "https://finance.yahoo.com/news/a",
            "https://finance.yahoo.com/news/b",
        ],
        kind="planned",
        as_of=date(2026, 4, 13),
        ticker_summary="aapl",
        out_dir=tmp_path,
    )
    text = path.read_text()
    assert text.startswith("# HOLD weekly snapshot")
    assert "## Summary" in text
    assert "## 상세" in text
    assert "## Citations" in text
    # each citation on its own bullet line for the grep -cE check in checkpoint
    lines = text.splitlines()
    cite_lines = [ln for ln in lines if ln.strip().startswith("- ") and (
        ln.strip().startswith("- http") or "accession" in ln
    )]
    assert len(cite_lines) >= 2


def test_accession_citation_accepted(tmp_path):
    path = emit_report(
        title="HOLD",
        sections=[{"heading": "S", "body": "HOLD body"}],
        citations=["accession:0000320193-24-000123", "https://a.example/x"],
        kind="planned",
        as_of=date(2026, 4, 13),
        ticker_summary="aapl",
        out_dir=tmp_path,
    )
    text = path.read_text()
    assert "accession:0000320193-24-000123" in text


def test_action_verb_present_in_title(tmp_path):
    path = emit_report(
        title="BUY signal on NVDA — strong momentum",
        sections=[{"heading": "S", "body": "BUY recommended"}],
        citations=["https://a.example", "https://b.example"],
        kind="planned",
        as_of=date(2026, 4, 13),
        ticker_summary="nvda",
        out_dir=tmp_path,
    )
    head_200 = path.read_text()[:200].upper()
    assert any(v in head_200 for v in ACTION_VERBS)


def test_action_verb_missing_is_detectable_but_emit_succeeds(tmp_path):
    path = emit_report(
        title="포트폴리오 요약 (중립)",
        sections=[{"heading": "S", "body": "단순 상태 보고"}],
        citations=["https://a.example", "https://b.example"],
        kind="planned",
        as_of=date(2026, 4, 13),
        ticker_summary="none",
        out_dir=tmp_path,
    )
    # emit succeeded
    assert path.exists()
    head_200 = path.read_text()[:200].upper()
    assert not any(v in head_200 for v in ACTION_VERBS)


def test_ticker_summary_sanitized(tmp_path):
    # spaces and oddities become underscores
    path = emit_report(
        title="HOLD",
        sections=[{"heading": "S", "body": "HOLD body"}],
        citations=["https://a.example", "https://b.example"],
        kind="planned",
        as_of=date(2026, 4, 13),
        ticker_summary="AAPL TSLA / NVDA",
        out_dir=tmp_path,
    )
    assert " " not in path.name
    assert "/" not in path.name
