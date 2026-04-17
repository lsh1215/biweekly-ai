"""Report emitter — writes planned / interrupt Markdown reports.

Contract (Sprint 2):

* ``citations`` length < 2 → ``ValueError`` (structural enforcement of PRD §5).
* Filename layout:
    * ``planned_<YYYYMMDD>_<ticker_summary>.md``
    * ``interrupt_<severity>_<YYYYMMDD>_<ticker>.md`` (Sprint 3 uses this).
* Markdown layout: ``# <title>`` then one ``## <heading>`` per section,
  finally ``## Citations`` as a ``-``-prefixed list (one citation per line —
  the checkpoint counts ``grep -cE 'https?://|accession'``).
* Action-verb presence in the first 200 chars is NOT enforced here (it
  belongs to the planner prompt). Emit succeeds either way; callers and
  tests can detect absence via ``ACTION_VERBS``.
"""

from __future__ import annotations

import logging
import re
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Literal, Sequence

logger = logging.getLogger(__name__)

ACTION_VERBS = ("BUY", "HOLD", "REDUCE", "WATCH", "REVIEW")
_DEFAULT_OUT = Path(__file__).resolve().parents[3] / "reports"
_SLUG_RE = re.compile(r"[^a-z0-9]+")


def _slugify(s: str) -> str:
    return _SLUG_RE.sub("_", s.lower()).strip("_") or "none"


def _render(title: str, sections: Sequence[dict], citations: Sequence[str]) -> str:
    parts: list[str] = [f"# {title}\n"]
    for s in sections:
        heading = s.get("heading", "").strip()
        body = s.get("body", "").rstrip()
        if not heading:
            continue
        parts.append(f"\n## {heading}\n\n{body}\n")
    parts.append("\n## Citations\n\n")
    for c in citations:
        parts.append(f"- {c}\n")
    return "".join(parts)


def emit_report(
    title: str,
    sections: Sequence[dict],
    citations: Sequence[str],
    *,
    kind: Literal["planned", "interrupt"] = "planned",
    severity: str | None = None,
    as_of: date | None = None,
    ticker: str | None = None,
    ticker_summary: str | None = None,
    out_dir: Path | None = None,
) -> Path:
    """Write a Markdown report and return its path."""
    if not isinstance(citations, (list, tuple)):
        raise TypeError("citations must be a list/tuple of strings")
    if len(citations) < 2:
        raise ValueError(
            f"emit_report requires ≥ 2 citations (got {len(citations)}) — "
            "PRD §5 hard gate"
        )

    stamp = (as_of or datetime.now(timezone.utc).date()).strftime("%Y%m%d")

    if kind == "interrupt":
        if not severity or not ticker:
            raise ValueError("interrupt reports require severity and ticker")
        fname = f"interrupt_{severity}_{stamp}_{ticker.upper()}.md"
    elif kind == "planned":
        slug = _slugify(ticker_summary or "portfolio")
        fname = f"planned_{stamp}_{slug}.md"
    else:
        raise ValueError(f"unknown kind: {kind!r}")

    out_root = Path(out_dir) if out_dir is not None else _DEFAULT_OUT
    out_root.mkdir(parents=True, exist_ok=True)
    path = out_root / fname

    content = _render(title, sections, citations)
    path.write_text(content)

    head = content[:200].upper()
    if not any(v in head for v in ACTION_VERBS):
        logger.warning(
            "emit_report: no action verb (%s) in first 200 chars of %s",
            "/".join(ACTION_VERBS),
            path.name,
        )

    return path
