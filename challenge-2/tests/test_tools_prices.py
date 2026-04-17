"""Sprint 1 — get_prices tool (TDD: tests before implementation).

Contract:
    get_prices(tickers, window_days, as_of=None) -> pd.DataFrame

Shape: long-format with columns
    [Date, ticker, Open, High, Low, Close, Adj Close, Volume]

Rules:
- as_of default = max Date across requested tickers' fixtures.
- window_days counts NYSE trading days: we return trading days in
  (as_of - window_days + 1 ... as_of], snapped to <= as_of.
- If as_of falls on a non-trading day (weekend / holiday), snap back
  to the previous NYSE trading day.
- Missing ticker fixture: raise FixtureNotFoundError (fixture-first).
- Empty ticker list: return empty DataFrame with the right columns.
- window_days <= 0: return empty DataFrame.
- Requesting dates outside the fixture range returns whatever overlap
  exists (possibly empty) — not an error.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from ria.fixtures import FixtureNotFoundError


# NYSE trading-day spine for 2026-03-02..2026-03-13 (Mon..Fri x2, no holidays).
_SPINE = [
    "2026-03-02", "2026-03-03", "2026-03-04", "2026-03-05", "2026-03-06",
    "2026-03-09", "2026-03-10", "2026-03-11", "2026-03-12", "2026-03-13",
]


def _write_price_csv(root: Path, ticker: str, dates: list[str], base: float = 100.0) -> None:
    prices = root / "prices"
    prices.mkdir(exist_ok=True)
    rows = []
    for i, d in enumerate(dates):
        c = base + i
        rows.append({
            "Date": d,
            "Adj Close": c,
            "Close": c,
            "High": c + 1.0,
            "Low": c - 1.0,
            "Open": c - 0.5,
            "Volume": 10000 + i,
        })
    pd.DataFrame(rows).to_csv(prices / f"{ticker}.csv", index=False)


@pytest.fixture
def price_root(tmp_path: Path) -> Path:
    _write_price_csv(tmp_path, "AAPL", _SPINE, base=150.0)
    _write_price_csv(tmp_path, "TSLA", _SPINE, base=250.0)
    return tmp_path


# -------- basic contract ------------------------------------------------------


def test_get_prices_returns_long_format(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    df = get_prices(["AAPL", "TSLA"], window_days=3, as_of=date(2026, 3, 13), root=price_root)

    assert isinstance(df, pd.DataFrame)
    assert {"Date", "ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"} == set(
        df.columns
    )
    # 3 trading days x 2 tickers = 6 rows
    assert len(df) == 6
    assert set(df["ticker"]) == {"AAPL", "TSLA"}
    # all dates in the expected 3-day window ending 2026-03-13
    assert set(df["Date"]) == {date(2026, 3, 11), date(2026, 3, 12), date(2026, 3, 13)}


def test_get_prices_as_of_defaults_to_max_fixture_date(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    df = get_prices(["AAPL"], window_days=2, root=price_root)
    # fixture max date is 2026-03-13 → two trading days = 03-12 and 03-13
    assert set(df["Date"]) == {date(2026, 3, 12), date(2026, 3, 13)}


def test_get_prices_weekend_as_of_snaps_back(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    # 2026-03-14 is Saturday → snap to Friday 03-13
    df = get_prices(
        ["AAPL"], window_days=1, as_of=date(2026, 3, 14), root=price_root
    )
    assert set(df["Date"]) == {date(2026, 3, 13)}


def test_get_prices_skips_weekends_in_window(price_root: Path) -> None:
    """5 trading days back from Friday 03-13 → Mon 03-09..Fri 03-13, no weekend."""
    from ria.tools.prices import get_prices

    df = get_prices(
        ["AAPL"], window_days=5, as_of=date(2026, 3, 13), root=price_root
    )
    assert set(df["Date"]) == {
        date(2026, 3, 9), date(2026, 3, 10), date(2026, 3, 11),
        date(2026, 3, 12), date(2026, 3, 13),
    }
    # no Sat/Sun
    for d in df["Date"]:
        assert d.weekday() < 5


def test_get_prices_window_exceeds_fixture_returns_available(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    # 20 trading days requested, only 10 in fixture → we return what we have
    df = get_prices(
        ["AAPL"], window_days=20, as_of=date(2026, 3, 13), root=price_root
    )
    assert len(df) == 10


def test_get_prices_missing_ticker_raises(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    with pytest.raises(FixtureNotFoundError):
        get_prices(["ZZZZ"], window_days=3, root=price_root)


def test_get_prices_empty_ticker_list(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    df = get_prices([], window_days=3, root=price_root)
    assert len(df) == 0
    assert {"Date", "ticker", "Close"}.issubset(df.columns)


def test_get_prices_zero_window_returns_empty(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    df = get_prices(["AAPL"], window_days=0, root=price_root)
    assert len(df) == 0


def test_get_prices_as_of_before_fixture_returns_empty(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    df = get_prices(
        ["AAPL"], window_days=5, as_of=date(2020, 1, 15), root=price_root
    )
    assert len(df) == 0


def test_get_prices_deterministic_on_repeated_call(price_root: Path) -> None:
    from ria.tools.prices import get_prices

    df1 = get_prices(["AAPL", "TSLA"], window_days=3, as_of=date(2026, 3, 13), root=price_root)
    df2 = get_prices(["AAPL", "TSLA"], window_days=3, as_of=date(2026, 3, 13), root=price_root)
    pd.testing.assert_frame_equal(df1, df2)
