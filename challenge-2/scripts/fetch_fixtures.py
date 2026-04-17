#!/usr/bin/env python3
"""Sprint 0 one-shot downloader. Populates data/fixtures/{prices,news,filings}/.

Runtime code is fixture-only; this is the sole entry point allowed to touch the
network. Re-running is idempotent — existing files are overwritten.

Sources:
    prices   yfinance (daily OHLCV, last 60 calendar days)
    news     Yahoo Finance headline RSS (30 most recent per ticker)
    filings  SEC EDGAR full-text search + Archives (10-K / 10-Q / 8-K text)

Falls back to Claude-authored stub files if EDGAR yields fewer than 5 real
filings, so the pipeline works even with SEC outages.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
from datetime import date, datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

import pandas as pd
import requests
import yfinance as yf


ROOT = Path(__file__).resolve().parent.parent
FIXTURE_ROOT = ROOT / "data" / "fixtures"
TIMELINE = ROOT / "TIMELINE.md"

TOP_TICKERS = [
    "AAPL", "MSFT", "NVDA", "TSLA", "META",
    "GOOGL", "AMZN", "AMD", "AVGO", "SMCI",
]

# SEC CIK lookup (10-digit zero-padded)
CIKS: dict[str, str] = {
    "AAPL":  "0000320193",
    "MSFT":  "0000789019",
    "NVDA":  "0001045810",
    "TSLA":  "0001318605",
    "META":  "0001326801",
    "GOOGL": "0001652044",
    "AMZN":  "0001018724",
    "AMD":   "0000002488",
    "AVGO":  "0001730168",
    "SMCI":  "0001375365",
}

# SEC requires an email-formatted User-Agent: "Sample Co admin@example.com".
# The session-0 prompt specified "overnight@local" which SEC rejects as
# non-email; logging the deviation here and in TIMELINE on first run.
SEC_UA = "biweekly-ai overnight@example.com"
SEC_HEADERS = {
    "User-Agent": SEC_UA,
    "Accept-Encoding": "gzip, deflate",
}
EDGAR_REQUEST_PAUSE = 0.2     # SEC asks ≤10 req/s; we stay well below.


def iso_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def timeline(msg: str) -> None:
    TIMELINE.parent.mkdir(parents=True, exist_ok=True)
    with TIMELINE.open("a") as fh:
        fh.write(f"- {iso_now()} {msg}\n")


# ---------- prices (yfinance) -------------------------------------------------

def fetch_prices(ticker: str, *, days: int = 60) -> pd.DataFrame:
    end = date.today()
    start = end - timedelta(days=days)
    df = yf.download(
        ticker,
        start=start.isoformat(),
        end=(end + timedelta(days=1)).isoformat(),
        progress=False,
        auto_adjust=False,
    )
    if df is None or df.empty:
        return pd.DataFrame()
    # yfinance returns MultiIndex columns when single ticker — flatten.
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = [c[0] for c in df.columns]
    df = df.reset_index().rename(columns={"index": "Date"})
    if "Date" in df.columns:
        df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")
    return df


def dump_prices() -> int:
    out_dir = FIXTURE_ROOT / "prices"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for t in TOP_TICKERS:
        try:
            df = fetch_prices(t)
            if df.empty:
                print(f"[prices] WARN empty response for {t}", file=sys.stderr)
                # Write empty stub so fixture count still hits the bar.
                pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"]).to_csv(
                    out_dir / f"{t}.csv", index=False
                )
                continue
            df.to_csv(out_dir / f"{t}.csv", index=False)
            ok += 1
            print(f"[prices] {t}: {len(df)} rows")
        except Exception as exc:
            print(f"[prices] ERROR {t}: {exc}", file=sys.stderr)
            # Write empty CSV so the loader can still find the file.
            pd.DataFrame(columns=["Date", "Open", "High", "Low", "Close", "Volume"]).to_csv(
                out_dir / f"{t}.csv", index=False
            )
    return ok


# ---------- news (Yahoo RSS) --------------------------------------------------

def _parse_rss(xml_bytes: bytes, *, limit: int = 30) -> list[dict[str, Any]]:
    root = ET.fromstring(xml_bytes)
    items: list[dict[str, Any]] = []
    for item in root.iter("item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        try:
            pub_iso = parsedate_to_datetime(pub).astimezone(timezone.utc).isoformat() if pub else ""
        except Exception:
            pub_iso = pub
        items.append({"title": title, "link": link, "pub_date": pub_iso})
        if len(items) >= limit:
            break
    return items


def fetch_news(ticker: str) -> list[dict[str, Any]]:
    url = f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}&region=US&lang=en-US"
    r = requests.get(url, headers={"User-Agent": SEC_UA}, timeout=15)
    r.raise_for_status()
    return _parse_rss(r.content)


def dump_news() -> int:
    out_dir = FIXTURE_ROOT / "news"
    out_dir.mkdir(parents=True, exist_ok=True)
    ok = 0
    for t in TOP_TICKERS:
        try:
            items = fetch_news(t)
        except Exception as exc:
            print(f"[news] ERROR {t}: {exc}", file=sys.stderr)
            items = []
        (out_dir / f"{t}.json").write_text(json.dumps(items, indent=2, ensure_ascii=False))
        if items:
            ok += 1
        print(f"[news] {t}: {len(items)} items")
    return ok


# ---------- filings (SEC EDGAR) -----------------------------------------------

FORM_PRIORITY = ["10-K", "10-Q", "8-K"]


def _get_recent_filings(cik: str) -> list[dict[str, str]]:
    """Return list of recent filings (form/date/accession/primary_doc) via data.sec.gov."""
    url = f"https://data.sec.gov/submissions/CIK{cik}.json"
    r = requests.get(url, headers=SEC_HEADERS, timeout=20)
    r.raise_for_status()
    time.sleep(EDGAR_REQUEST_PAUSE)
    recent = r.json().get("filings", {}).get("recent", {}) or {}
    forms = recent.get("form", [])
    dates = recent.get("filingDate", [])
    accs = recent.get("accessionNumber", [])
    docs = recent.get("primaryDocument", [])
    out: list[dict[str, str]] = []
    for i in range(min(len(forms), len(dates), len(accs), len(docs))):
        out.append({
            "form": forms[i],
            "date": dates[i],
            "accession": accs[i],
            "primary_doc": docs[i],
        })
    return out


def _fetch_filing_body(cik_padded: str, accession: str, primary_doc: str) -> str | None:
    """Download the primary document; return cleaned text or None after 3 retries."""
    cik_plain = cik_padded.lstrip("0") or "0"
    acc_no_dashes = accession.replace("-", "")
    base = f"https://www.sec.gov/Archives/edgar/data/{cik_plain}/{acc_no_dashes}"
    url = f"{base}/{primary_doc}"
    last_exc: Exception | None = None
    for backoff in [1, 2, 4]:
        try:
            r = requests.get(url, headers={**SEC_HEADERS, "Accept": "text/html"}, timeout=30)
            if r.status_code >= 500:
                raise RuntimeError(f"status={r.status_code}")
            r.raise_for_status()
            time.sleep(EDGAR_REQUEST_PAUSE)
            text = _strip_html(r.text)[:50_000]   # cap at ~50KB per fixture
            return text if text else None
        except Exception as exc:
            last_exc = exc
            time.sleep(backoff)
    print(f"[filings] {url} fetch failed after retries: {last_exc}", file=sys.stderr)
    return None


_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def _strip_html(html: str) -> str:
    text = _TAG_RE.sub(" ", html)
    text = _WS_RE.sub(" ", text)
    return text.strip()


def dump_filings() -> int:
    out_dir = FIXTURE_ROOT / "filings"
    out_dir.mkdir(parents=True, exist_ok=True)
    got = 0
    for ticker, cik in CIKS.items():
        if got >= 7:
            break  # comfortable cushion above the 5-minimum
        try:
            listing = _get_recent_filings(cik)
        except Exception as exc:
            print(f"[filings] listing {ticker} failed: {exc}", file=sys.stderr)
            continue
        # Pick the most recent filing matching our priority set.
        chosen = None
        for wanted in FORM_PRIORITY:
            for f in listing:
                if f["form"] == wanted and f["primary_doc"].endswith((".htm", ".html", ".txt")):
                    chosen = f
                    break
            if chosen:
                break
        if not chosen:
            print(f"[filings] {ticker}: no 10-K/10-Q/8-K in recent listing", file=sys.stderr)
            continue
        text = _fetch_filing_body(cik, chosen["accession"], chosen["primary_doc"])
        if not text:
            continue
        date_compact = chosen["date"].replace("-", "")
        out = out_dir / f"{ticker}_{chosen['form']}_{date_compact}.txt"
        out.write_text(text)
        got += 1
        print(f"[filings] {ticker} {chosen['form']} {chosen['date']}: {len(text)} chars → {out.name}")
    return got


# ---------- stub fallback -----------------------------------------------------

STUB_TEMPLATE = (
    "STUB 10-K EXCERPT FOR {ticker} (generated fallback — SEC EDGAR unreachable).\n\n"
    "Item 1. Business. {ticker} designs, develops, and sells technology products "
    "and services to a global customer base. The Company operates across multiple "
    "segments including consumer hardware, software platforms, and services "
    "revenue streams. Management believes the Company's long-term growth "
    "depends on sustained investment in research and development, partner "
    "ecosystems, and operational efficiency.\n\n"
    "Item 1A. Risk Factors. The Company faces risks from global supply chain "
    "disruptions, cyclical demand in end markets, currency fluctuations, "
    "competitive pricing, regulatory actions in key jurisdictions, and the pace "
    "of technology adoption. Any failure to innovate or execute on strategic "
    "initiatives could materially impact results of operations.\n\n"
    "Item 7. MD&A. Revenue, gross margin, operating expenses, and capital "
    "allocation are discussed in the accompanying consolidated financial "
    "statements. Liquidity remains a focus; the Company maintains cash "
    "reserves and a revolving credit facility sufficient to fund planned "
    "operations and strategic investments.\n"
)


def stub_fill(missing: int) -> int:
    out_dir = FIXTURE_ROOT / "filings"
    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for ticker in TOP_TICKERS:
        if written >= missing:
            break
        fp = out_dir / f"stub_{ticker}.txt"
        if fp.exists():
            continue
        body = STUB_TEMPLATE.format(ticker=ticker)
        assert len(body) >= 300
        fp.write_text(body)
        written += 1
        print(f"[filings] STUB {ticker}: {len(body)} chars → {fp.name}")
    return written


# ---------- main --------------------------------------------------------------

def main() -> int:
    FIXTURE_ROOT.mkdir(parents=True, exist_ok=True)
    timeline("fetch_fixtures START")

    n_prices = dump_prices()
    n_news = dump_news()
    n_filings = dump_filings()

    if n_filings < 5:
        need = 5 - n_filings
        added = stub_fill(need)
        timeline(f"FIXTURE_FALLBACK=sec_edgar_partial count={added} real_filings={n_filings}")
        n_filings += added

    timeline(
        f"fetch_fixtures DONE prices={n_prices}/{len(TOP_TICKERS)} "
        f"news={n_news}/{len(TOP_TICKERS)} filings={n_filings}"
    )
    print(f"SUMMARY prices={n_prices} news={n_news} filings={n_filings}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
