"""Price-lookup tool for the RIA agent.

Reads fixture CSVs via `ria.fixtures.load_prices`, snaps `as_of` to the
nearest prior NYSE trading day, and returns the last `window_days` of
trading-day rows per ticker in long format.

NYSE calendar comes from `pandas_market_calendars` so weekends and US
market holidays are handled consistently.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd
import pandas_market_calendars as mcal

from ria.fixtures import load_prices

_COLUMNS = ["Date", "ticker", "Open", "High", "Low", "Close", "Adj Close", "Volume"]
_nyse = mcal.get_calendar("NYSE")


def _trading_days(start: date, end: date) -> list[date]:
    """NYSE trading days in [start, end], inclusive, sorted ascending."""
    if start > end:
        return []
    sched = _nyse.schedule(start_date=start.isoformat(), end_date=end.isoformat())
    return [d.date() for d in sched.index]


def _snap_to_trading_day(as_of: date) -> date | None:
    """Return the last NYSE trading day <= as_of (within ~14-day lookback)."""
    days = _trading_days(as_of - timedelta(days=14), as_of)
    return days[-1] if days else None


def _fixture_max_date(tickers: list[str], root: Path | None) -> date | None:
    maxes: list[date] = []
    for t in tickers:
        df = load_prices(t, root=root)
        if not df.empty:
            maxes.append(max(df["Date"]))
    return max(maxes) if maxes else None


def get_prices(
    tickers: list[str],
    window_days: int,
    as_of: date | None = None,
    *,
    root: Path | None = None,
) -> pd.DataFrame:
    """Return the last `window_days` of NYSE trading days for each ticker.

    Parameters
    ----------
    tickers:
        Symbols to look up. Each must have a fixture CSV or
        FixtureNotFoundError is raised.
    window_days:
        Count of trading days to return, ending at (and including) `as_of`.
        <=0 yields an empty frame.
    as_of:
        Reference date. Default = max Date across the requested tickers'
        fixtures. Snapped back to the nearest prior NYSE trading day if it
        falls on a weekend/holiday.
    root:
        Override fixture root (tests).
    """
    if not tickers or window_days <= 0:
        return pd.DataFrame(columns=_COLUMNS)

    if as_of is None:
        as_of = _fixture_max_date(tickers, root)
        if as_of is None:
            return pd.DataFrame(columns=_COLUMNS)

    anchor = _snap_to_trading_day(as_of)
    if anchor is None:
        return pd.DataFrame(columns=_COLUMNS)

    # Generous lookback to guarantee we cover window_days trading days even
    # with a long holiday stretch. 2 * window_days + 14 is >> worst case.
    lookback_start = anchor - timedelta(days=max(window_days * 2 + 14, 30))
    days = _trading_days(lookback_start, anchor)
    window = days[-window_days:]
    if not window:
        return pd.DataFrame(columns=_COLUMNS)
    window_set = set(window)

    rows: list[pd.DataFrame] = []
    for t in tickers:
        df = load_prices(t, root=root)
        df = df[df["Date"].isin(window_set)].copy()
        df["ticker"] = t.upper()
        rows.append(df)

    out = pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=_COLUMNS)
    out = out[[c for c in _COLUMNS if c in out.columns]]
    out = out.sort_values(["Date", "ticker"], kind="stable").reset_index(drop=True)
    # enforce all expected columns exist even on empty frames
    for c in _COLUMNS:
        if c not in out.columns:
            out[c] = pd.Series(dtype="float64")
    return out[_COLUMNS]
