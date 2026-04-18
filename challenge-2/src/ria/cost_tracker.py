"""Claude-API cost ledger (Sprint 4).

Every live (or replay-with-usage-metadata) model call should call
``record(label, model, input_tokens, output_tokens)``. The accumulating
ledger lives at ``reports/cost_ledger.jsonl`` and ``write_summary`` renders
the human-readable ``reports/cost_summary.md`` that VERIFY.sh parses.

Summary file format — STRICT CONTRACT with ``VERIFY.sh`` step 10:

    total $12.40
    planned_20260413: input=3214 output=892 usd=0.0421
    interrupt_P0_20260415_TSLA: input=2891 output=720 usd=0.0384
    classify_evt_tsla_earnings_miss: input=512 output=68 usd=0.0014

The first line MUST match ``^total \\$[0-9]+\\.[0-9]+$`` exactly — no
markdown heading, no colon, no leading/trailing whitespace. That regex is
what ``awk 'NR==1 && /^total \\$[0-9]+\\.[0-9]+/'`` in VERIFY.sh keys off
of; drifting this file without updating VERIFY.sh silently breaks the gate.

Published Anthropic rates (last verified Jan 2026, same table as
``scripts/cost_probe.py``):

* Opus  4.7: $15 / $75 per MTok (input / output)
* Haiku 4.5: $1  / $5  per MTok
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Optional

# Single source of truth for the budget gate.
BUDGET_USD_HARD = 50.0
BUDGET_USD_WARN = 40.0

# {model_id_prefix: (input_usd_per_mtok, output_usd_per_mtok)}
# We match on prefix to be resilient to minor suffix changes (e.g. `-20260101`).
_PRICES: list[tuple[str, tuple[float, float]]] = [
    ("claude-opus",  (15.0, 75.0)),
    ("claude-haiku", (1.0,   5.0)),
    ("claude-sonnet",(3.0,  15.0)),   # defensive: not used today but priced.
]

DEFAULT_LEDGER_PATH = Path("reports") / "cost_ledger.jsonl"
DEFAULT_SUMMARY_PATH = Path("reports") / "cost_summary.md"


def _rates_for(model: str) -> tuple[float, float]:
    for prefix, rates in _PRICES:
        if model.startswith(prefix):
            return rates
    raise ValueError(f"unknown model {model!r} — add to cost_tracker._PRICES")


def compute_usd(model: str, input_tokens: int, output_tokens: int) -> float:
    in_rate, out_rate = _rates_for(model)
    return (input_tokens / 1_000_000.0) * in_rate + (output_tokens / 1_000_000.0) * out_rate


@dataclass(frozen=True)
class LedgerEntry:
    label: str
    model: str
    input_tokens: int
    output_tokens: int
    usd: float


def record(
    label: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    *,
    ledger_path: Optional[Path] = None,
) -> LedgerEntry:
    """Append one usage entry to the JSONL ledger and return the row."""
    path = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    entry = LedgerEntry(
        label=label,
        model=model,
        input_tokens=int(input_tokens),
        output_tokens=int(output_tokens),
        usd=compute_usd(model, int(input_tokens), int(output_tokens)),
    )
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(entry.__dict__, ensure_ascii=False) + "\n")
    return entry


def load_ledger(ledger_path: Path) -> list[dict]:
    path = Path(ledger_path)
    if not path.exists():
        return []
    out: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        out.append(json.loads(line))
    return out


def _format_summary(entries: Iterable[dict]) -> tuple[str, float]:
    rows = list(entries)
    total = sum(float(r.get("usd", 0.0)) for r in rows)
    # strict first line — no colon, no markdown heading, no trailing punctuation
    lines = [f"total ${total:.2f}"]
    for r in rows:
        label = str(r.get("label", "")).strip() or "unknown"
        model = str(r.get("model", ""))
        n_in = int(r.get("input_tokens", 0))
        n_out = int(r.get("output_tokens", 0))
        usd = float(r.get("usd", compute_usd(model, n_in, n_out) if model else 0.0))
        lines.append(f"{label}: input={n_in} output={n_out} usd={usd:.4f}")
    return "\n".join(lines) + "\n", total


def write_summary(
    ledger_path: Optional[Path] = None,
    summary_path: Optional[Path] = None,
) -> float:
    """Render the ledger to ``cost_summary.md``. Raises if total > $50.

    Even when the budget is blown, the summary file is still written — that
    way the user can ``cat reports/cost_summary.md`` to see the breakdown
    of what went wrong.
    """
    lp = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER_PATH
    sp = Path(summary_path) if summary_path is not None else DEFAULT_SUMMARY_PATH
    sp.parent.mkdir(parents=True, exist_ok=True)

    entries = load_ledger(lp)
    content, total = _format_summary(entries)
    sp.write_text(content, encoding="utf-8")

    if total > BUDGET_USD_HARD:
        raise RuntimeError(
            f"cost budget exceeded: total=${total:.2f} > ${BUDGET_USD_HARD:.2f}"
        )
    return total


def reset_ledger(ledger_path: Optional[Path] = None) -> None:
    """Remove the ledger file if present (idempotent)."""
    lp = Path(ledger_path) if ledger_path is not None else DEFAULT_LEDGER_PATH
    if lp.exists():
        lp.unlink()
