"""cost_probe.py - static estimate of total LLM cost for the overnight pipeline.

CLAUDE.md §12: NO live API calls. NO ANTHROPIC_API_KEY env-var check.
NO `claude -p ping` preflight. Pure arithmetic on PRD §8 numbers.
"""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LOG = ROOT / "logs" / "cost_probe.txt"

# PRD §8 numbers (in USD).
SPRINT1_LIVE_RECORDING_USD = 0.53     # 4 fmt x (writer + critic) live capture
DOGFOOD_USD = 0.26                    # 4 format x 1 topic dogfood
RETRY_BUFFER_USD = 1.06               # 2 retries on Sprint 1 capture
SAFETY_MARGIN_USD = 5.65

CAP_USD = 7.50

# Per-call estimate used in sprint 1 recording
PER_CALL_USD = 0.066
NUM_LIVE_CALLS_SPRINT1 = 8            # 4 fmt x 2 stages
NUM_DOGFOOD_CALLS = 4


def estimate() -> dict:
    total = (
        SPRINT1_LIVE_RECORDING_USD
        + DOGFOOD_USD
        + RETRY_BUFFER_USD
        + SAFETY_MARGIN_USD
    )
    return {
        "estimated_total_usd": round(total, 2),
        "cap_usd": CAP_USD,
        "within_cap": total <= CAP_USD,
        "breakdown": {
            "sprint1_live_recording_usd": SPRINT1_LIVE_RECORDING_USD,
            "dogfood_usd": DOGFOOD_USD,
            "retry_buffer_usd": RETRY_BUFFER_USD,
            "safety_margin_usd": SAFETY_MARGIN_USD,
        },
        "calls": {
            "sprint1_live_calls": NUM_LIVE_CALLS_SPRINT1,
            "dogfood_calls": NUM_DOGFOOD_CALLS,
            "per_call_usd": PER_CALL_USD,
        },
        "captured_at": datetime.now(tz=timezone.utc).isoformat(timespec="seconds"),
        "notes": "Static estimate only. No live API call performed (CLAUDE.md sec 12).",
    }


def main() -> int:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    data = estimate()
    # First line MUST match: estimated_total_usd=<float>
    lines = [
        f"estimated_total_usd={data['estimated_total_usd']}",
        f"cap_usd={data['cap_usd']}",
        f"within_cap={str(data['within_cap']).lower()}",
        f"captured_at={data['captured_at']}",
        "",
        "# Breakdown:",
    ]
    for k, v in data["breakdown"].items():
        lines.append(f"  {k}={v}")
    lines.append("")
    lines.append("# Calls:")
    for k, v in data["calls"].items():
        lines.append(f"  {k}={v}")
    lines.append("")
    lines.append(f"# Notes: {data['notes']}")
    LOG.write_text("\n".join(lines) + "\n", encoding="utf-8")

    # Also dump JSON next to it for programmatic checks
    (LOG.with_suffix(".json")).write_text(
        json.dumps(data, indent=2) + "\n", encoding="utf-8"
    )
    print(lines[0])
    if not data["within_cap"]:
        print(f"WARNING: estimated_total_usd > cap_usd ({CAP_USD})")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
