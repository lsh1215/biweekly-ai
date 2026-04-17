"""Sprint 1 — get_news tool.

Contract:
    get_news(ticker, last_n_days) -> list[Article]
    Article = {title: str, link: str, pub_date: str (ISO-8601)}

Rules:
- Anchors to the fixture's most recent pub_date (deterministic).
- last_n_days is a *calendar* day window [anchor - last_n_days, anchor].
- Sorted newest-first.
- Missing ticker → FixtureNotFoundError.
- last_n_days <= 0 → empty list.
- Malformed/missing pub_date entries are skipped (defensive against fixture drift).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from ria.fixtures import FixtureNotFoundError


def _write_news(root: Path, ticker: str, items: list[dict]) -> None:
    news = root / "news"
    news.mkdir(exist_ok=True)
    (news / f"{ticker}.json").write_text(json.dumps(items))


@pytest.fixture
def news_root(tmp_path: Path) -> Path:
    _write_news(
        tmp_path,
        "AAPL",
        [
            {"title": "Today", "link": "u1", "pub_date": "2026-04-17T12:00:00+00:00"},
            {"title": "Yesterday", "link": "u2", "pub_date": "2026-04-16T09:00:00+00:00"},
            {"title": "Last week", "link": "u3", "pub_date": "2026-04-10T09:00:00+00:00"},
            {"title": "Last month", "link": "u4", "pub_date": "2026-03-17T09:00:00+00:00"},
        ],
    )
    return tmp_path


def test_get_news_returns_list_of_dicts(news_root: Path) -> None:
    from ria.tools.news import get_news

    items = get_news("AAPL", last_n_days=30, root=news_root)
    assert isinstance(items, list)
    assert all({"title", "link", "pub_date"}.issubset(a.keys()) for a in items)


def test_get_news_filters_by_recency_window(news_root: Path) -> None:
    from ria.tools.news import get_news

    # 2-day window from anchor 2026-04-17 → only "Today" (04-17) and "Yesterday" (04-16)
    items = get_news("AAPL", last_n_days=2, root=news_root)
    assert [a["title"] for a in items] == ["Today", "Yesterday"]


def test_get_news_sorted_newest_first(news_root: Path) -> None:
    from ria.tools.news import get_news

    items = get_news("AAPL", last_n_days=365, root=news_root)
    titles = [a["title"] for a in items]
    assert titles == ["Today", "Yesterday", "Last week", "Last month"]


def test_get_news_zero_days_returns_empty(news_root: Path) -> None:
    from ria.tools.news import get_news

    assert get_news("AAPL", last_n_days=0, root=news_root) == []


def test_get_news_negative_days_returns_empty(news_root: Path) -> None:
    from ria.tools.news import get_news

    assert get_news("AAPL", last_n_days=-3, root=news_root) == []


def test_get_news_missing_ticker_raises(news_root: Path) -> None:
    from ria.tools.news import get_news

    with pytest.raises(FixtureNotFoundError):
        get_news("ZZZZ", last_n_days=5, root=news_root)


def test_get_news_skips_malformed_entries(tmp_path: Path) -> None:
    from ria.tools.news import get_news

    _write_news(
        tmp_path,
        "BAD",
        [
            {"title": "ok", "link": "u1", "pub_date": "2026-04-17T12:00:00+00:00"},
            {"title": "no date", "link": "u2"},  # missing pub_date
            {"title": "garbage date", "link": "u3", "pub_date": "???"},
        ],
    )
    items = get_news("BAD", last_n_days=30, root=tmp_path)
    assert [a["title"] for a in items] == ["ok"]


def test_get_news_deterministic(news_root: Path) -> None:
    from ria.tools.news import get_news

    a = get_news("AAPL", last_n_days=7, root=news_root)
    b = get_news("AAPL", last_n_days=7, root=news_root)
    assert a == b
