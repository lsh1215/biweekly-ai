"""Sprint 0 — fixture loader unit tests (TDD: written before fixtures.py).

Covers:
- empty directory case
- missing ticker case
- date range out of bounds
- stub filing file inclusion
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ria.fixtures import (
    FixtureNotFoundError,
    iter_filings,
    load_news,
    load_prices,
)


@pytest.fixture
def empty_fixture_root(tmp_path: Path) -> Path:
    (tmp_path / "prices").mkdir()
    (tmp_path / "news").mkdir()
    (tmp_path / "filings").mkdir()
    return tmp_path


@pytest.fixture
def sample_fixture_root(tmp_path: Path) -> Path:
    prices = tmp_path / "prices"
    news = tmp_path / "news"
    filings = tmp_path / "filings"
    prices.mkdir()
    news.mkdir()
    filings.mkdir()

    # Prices CSV (yfinance-like format)
    df = pd.DataFrame(
        {
            "Date": ["2026-03-01", "2026-03-02", "2026-03-03"],
            "Open": [100.0, 101.0, 102.0],
            "High": [103.0, 104.0, 105.0],
            "Low": [99.0, 100.0, 101.0],
            "Close": [102.0, 103.0, 104.0],
            "Volume": [10000, 11000, 12000],
        }
    )
    df.to_csv(prices / "AAPL.csv", index=False)

    (news / "AAPL.json").write_text(
        json.dumps(
            [
                {
                    "title": "Apple beats estimates",
                    "link": "https://example.com/a",
                    "pub_date": "2026-03-03T10:00:00Z",
                },
                {
                    "title": "Supply chain update",
                    "link": "https://example.com/b",
                    "pub_date": "2026-03-02T09:00:00Z",
                },
            ]
        )
    )

    (filings / "AAPL_10-K_20261015.txt").write_text("Form 10-K filing body for AAPL ...")
    (filings / "stub_META.txt").write_text("STUB 10-K excerpt for META ..." * 10)
    return tmp_path


# -------- load_prices ---------------------------------------------------------

def test_load_prices_returns_dataframe(sample_fixture_root: Path) -> None:
    df = load_prices("AAPL", root=sample_fixture_root)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3
    assert {"Open", "Close", "Volume"}.issubset(df.columns)


def test_load_prices_missing_ticker_raises(sample_fixture_root: Path) -> None:
    with pytest.raises(FixtureNotFoundError):
        load_prices("ZZZZ", root=sample_fixture_root)


def test_load_prices_empty_dir_raises(empty_fixture_root: Path) -> None:
    with pytest.raises(FixtureNotFoundError):
        load_prices("AAPL", root=empty_fixture_root)


def test_load_prices_filters_by_date_range(sample_fixture_root: Path) -> None:
    df = load_prices(
        "AAPL",
        root=sample_fixture_root,
        start=date(2026, 3, 2),
        end=date(2026, 3, 2),
    )
    assert len(df) == 1


def test_load_prices_date_out_of_range_returns_empty(sample_fixture_root: Path) -> None:
    """Out-of-range: return empty DataFrame, not raise."""
    df = load_prices(
        "AAPL",
        root=sample_fixture_root,
        start=date(2030, 1, 1),
        end=date(2030, 12, 31),
    )
    assert len(df) == 0
    assert isinstance(df, pd.DataFrame)


# -------- load_news -----------------------------------------------------------

def test_load_news_returns_list(sample_fixture_root: Path) -> None:
    items = load_news("AAPL", root=sample_fixture_root)
    assert isinstance(items, list)
    assert len(items) == 2
    assert items[0]["title"] == "Apple beats estimates"


def test_load_news_missing_ticker_raises(sample_fixture_root: Path) -> None:
    with pytest.raises(FixtureNotFoundError):
        load_news("ZZZZ", root=sample_fixture_root)


def test_load_news_empty_dir_raises(empty_fixture_root: Path) -> None:
    with pytest.raises(FixtureNotFoundError):
        load_news("AAPL", root=empty_fixture_root)


# -------- iter_filings --------------------------------------------------------

def test_iter_filings_includes_real_and_stub(sample_fixture_root: Path) -> None:
    filings = list(iter_filings(root=sample_fixture_root))
    # One real (AAPL_10-K_*) + one stub (stub_META.txt)
    assert len(filings) == 2
    paths = [f.path.name for f in filings]
    assert any(n.startswith("stub_") for n in paths)
    assert any(n.startswith("AAPL_10-K") for n in paths)


def test_iter_filings_flags_stubs(sample_fixture_root: Path) -> None:
    filings = list(iter_filings(root=sample_fixture_root))
    stubs = [f for f in filings if f.is_stub]
    real = [f for f in filings if not f.is_stub]
    assert len(stubs) == 1
    assert len(real) == 1
    assert stubs[0].ticker == "META"
    assert real[0].ticker == "AAPL"


def test_iter_filings_empty_dir_yields_nothing(empty_fixture_root: Path) -> None:
    assert list(iter_filings(root=empty_fixture_root)) == []


def test_iter_filings_ticker_filter(sample_fixture_root: Path) -> None:
    """Caller can restrict to a single ticker."""
    filings = list(iter_filings(root=sample_fixture_root, ticker="META"))
    assert len(filings) == 1
    assert filings[0].is_stub is True
