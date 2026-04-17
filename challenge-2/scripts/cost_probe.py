#!/usr/bin/env python3
"""Sprint 0 cost probe — estimate overnight Claude API spend.

Primary path: call Haiku 4.5 once, read exact input/output token counts from
`response.usage`, multiply by published per-MTok rates, then scale to the
overnight budget envelope.

Fallback path: if ANTHROPIC_API_KEY is missing OR the SDK call fails, use
synthetic token counts at the same published rates. The last line of output
is always `estimated_total_usd=X.XX` so Sprint 4's cost_summary.md parser
and checkpoint_sprint0.sh `grep estimated_total_usd` both stay happy.

The figure produced is an *estimate*; Sprint 4's journal captures the true
per-call usage and supersedes this file.
"""

from __future__ import annotations

import os
import sys
import traceback

# Published prices (USD per 1M tokens) — last verified Jan 2026 cutoff.
# Source: https://www.anthropic.com/pricing
PRICES_PER_MTOK = {
    "opus":  {"input": 15.00, "output": 75.00},   # Claude Opus 4 family
    "haiku": {"input":  1.00, "output":  5.00},   # Claude Haiku 4.5
}

# Overnight call envelope — upper-bound projection used for budget gating.
CALL_PLAN = [
    # (model, input_tokens, output_tokens, description)
    ("opus",  8_000,  1_200, "planned_weekly_healthcheck (1x/week)"),
    ("opus",  6_000,   900,  "interrupt_P0_report x2"),
    ("opus",  6_000,   900,  "interrupt_P0_report x2"),
    ("haiku",   600,    30,  "severity_classify x5"),
    ("haiku",   600,    30,  "severity_classify x5"),
    ("haiku",   600,    30,  "severity_classify x5"),
    ("haiku",   600,    30,  "severity_classify x5"),
    ("haiku",   600,    30,  "severity_classify x5"),
]


def usd_for(model: str, n_in: int, n_out: int) -> float:
    price = PRICES_PER_MTOK[model]
    return (n_in / 1_000_000.0) * price["input"] + (n_out / 1_000_000.0) * price["output"]


def planned_total() -> float:
    return sum(usd_for(m, i, o) for (m, i, o, _) in CALL_PLAN)


def try_live_probe() -> tuple[int, int] | None:
    """Make one tiny Haiku call; return (input_tokens, output_tokens) or None."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return None
    try:
        import anthropic

        client = anthropic.Anthropic(api_key=api_key)
        resp = client.messages.create(
            model="claude-haiku-4-5",
            max_tokens=16,
            messages=[{"role": "user", "content": "Reply with the single word: ok"}],
        )
        usage = resp.usage
        return (int(usage.input_tokens), int(usage.output_tokens))
    except Exception:
        traceback.print_exc(file=sys.stderr)
        return None


def main() -> int:
    mode = "LIVE"
    live = try_live_probe()
    if live is None:
        mode = "FALLBACK (no ANTHROPIC_API_KEY or API error — using published rates only)"
        probe_in, probe_out = 24, 4           # representative tiny call
        probe_usd = usd_for("haiku", probe_in, probe_out)
    else:
        probe_in, probe_out = live
        probe_usd = usd_for("haiku", probe_in, probe_out)

    total = planned_total()

    print(f"cost_probe mode: {mode}")
    print(f"probe_call: model=haiku input_tokens={probe_in} output_tokens={probe_out} usd={probe_usd:.6f}")
    print("projected overnight envelope:")
    for (m, n_in, n_out, desc) in CALL_PLAN:
        usd = usd_for(m, n_in, n_out)
        print(f"  {m:5s} in={n_in:>6d} out={n_out:>5d} usd={usd:.4f}  # {desc}")
    print(f"budget_cap_usd=50.00")
    # Final line MUST remain exactly this format — Sprint 4 parser depends on it.
    print(f"estimated_total_usd={total:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
