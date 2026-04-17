"""News-lookup tool for the RIA agent.

Reads fixture JSON via `ria.fixtures.load_news` and filters to the last
N calendar days ending at the fixture's most recent `pub_date` (so tests
are deterministic without a wall-clock dependency).
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, TypedDict

from ria.fixtures import load_news


class Article(TypedDict):
    title: str
    link: str
    pub_date: str


def _parse(pub: Any) -> datetime | None:
    if not isinstance(pub, str) or not pub:
        return None
    try:
        # accept trailing 'Z' as UTC (fromisoformat in 3.11+ handles offsets natively)
        dt = datetime.fromisoformat(pub.replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def get_news(
    ticker: str,
    last_n_days: int,
    *,
    root: Path | None = None,
) -> list[Article]:
    """Return articles for `ticker` within `last_n_days` of the fixture anchor.

    Anchor = max pub_date in the fixture. A fresh RIA run with an updated
    fixture shifts the anchor forward automatically.
    """
    raw = load_news(ticker, root=root)
    if last_n_days <= 0:
        return []

    valid: list[tuple[datetime, Article]] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        dt = _parse(entry.get("pub_date"))
        if dt is None:
            continue
        if "title" not in entry or "link" not in entry:
            continue
        valid.append(
            (
                dt,
                {
                    "title": entry["title"],
                    "link": entry["link"],
                    "pub_date": entry["pub_date"],
                },
            )
        )

    if not valid:
        return []

    anchor = max(dt for dt, _ in valid)
    cutoff = anchor - timedelta(days=last_n_days)
    filtered = [(dt, a) for dt, a in valid if dt >= cutoff]
    filtered.sort(key=lambda x: x[0], reverse=True)
    return [a for _, a in filtered]
