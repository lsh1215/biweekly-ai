"""Fixture loader — read pre-downloaded prices / news / filings from disk.

Runtime code must never hit the network; Sprint 0's `scripts/fetch_fixtures.py`
is the only entry point allowed to fetch. These loaders centralize the
filesystem convention:

    <root>/
        prices/{TICKER}.csv          (yfinance-style OHLCV)
        news/{TICKER}.json           (list[{title, link, pub_date}])
        filings/{TICKER}_{FORM}_{YYYYMMDD}.txt   (real)
        filings/stub_{TICKER}.txt    (offline fallback)
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterator

import json
import pandas as pd


DEFAULT_FIXTURE_ROOT = Path(__file__).resolve().parents[2] / "data" / "fixtures"


class FixtureNotFoundError(FileNotFoundError):
    """Raised when a required fixture file is absent — runtime is fixture-first."""


@dataclass(frozen=True)
class FilingRef:
    path: Path
    ticker: str
    form: str | None
    is_stub: bool


# -------- prices --------------------------------------------------------------

def _resolve_root(root: Path | None) -> Path:
    return Path(root) if root is not None else DEFAULT_FIXTURE_ROOT


def load_prices(
    ticker: str,
    *,
    root: Path | None = None,
    start: date | None = None,
    end: date | None = None,
) -> pd.DataFrame:
    """Load OHLCV CSV for `ticker`, optionally filtered to [start, end] inclusive.

    Missing file → FixtureNotFoundError.
    Out-of-range date filter → empty DataFrame (not an error).
    """
    base = _resolve_root(root) / "prices"
    fp = base / f"{ticker.upper()}.csv"
    if not fp.exists():
        raise FixtureNotFoundError(f"price fixture missing: {fp}")
    df = pd.read_csv(fp)
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"]).dt.date
        if start is not None:
            df = df[df["Date"] >= start]
        if end is not None:
            df = df[df["Date"] <= end]
        df = df.reset_index(drop=True)
    return df


# -------- news ----------------------------------------------------------------

def load_news(ticker: str, *, root: Path | None = None) -> list[dict[str, Any]]:
    """Load news fixture JSON (list of dicts). Missing → FixtureNotFoundError."""
    fp = _resolve_root(root) / "news" / f"{ticker.upper()}.json"
    if not fp.exists():
        raise FixtureNotFoundError(f"news fixture missing: {fp}")
    return json.loads(fp.read_text())


# -------- filings -------------------------------------------------------------

def _parse_filing_name(name: str) -> tuple[str, str | None, bool]:
    """Return (ticker, form, is_stub) from filename conventions."""
    stem = name.removesuffix(".txt")
    if stem.startswith("stub_"):
        return stem.removeprefix("stub_").upper(), None, True
    # real: TICKER_FORM_DATE  (split once from the left)
    parts = stem.split("_", 2)
    ticker = parts[0].upper()
    form = parts[1] if len(parts) > 1 else None
    return ticker, form, False


def iter_filings(
    *, root: Path | None = None, ticker: str | None = None
) -> Iterator[FilingRef]:
    """Yield FilingRef for every .txt file under filings/, optionally ticker-filtered."""
    base = _resolve_root(root) / "filings"
    if not base.exists():
        return
    tkr = ticker.upper() if ticker else None
    for fp in sorted(base.glob("*.txt")):
        t, form, is_stub = _parse_filing_name(fp.name)
        if tkr and t != tkr:
            continue
        yield FilingRef(path=fp, ticker=t, form=form, is_stub=is_stub)
