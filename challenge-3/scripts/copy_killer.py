"""copy-killer — LLM-free AI-tell scorer.

Usage:
  python scripts/copy_killer.py <md_path> [--threshold 0.35]

Computes 6 indicators (PRD §3 D6), weighted sum gives ai_score in [0, 1].
ai_score > threshold → BLOCKED; otherwise PASS.

Deterministic threshold tuner (S3): given a list of pre-computed scores and
current weights/threshold, produce a new state. Pure function, no LLM, no
randomness.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

import copy_killer_metrics as km

DEFAULT_WEIGHTS = {
    "sentence_length_variance": 0.20,
    "avg_syllable_length": 0.10,
    "connector_frequency": 0.20,
    "r1_r7_residual": 0.30,
    "monotone_ending_ratio": 0.15,
    "generic_modifier_density": 0.05,
}

DEFAULT_THRESHOLD = 0.35
THRESHOLD_MIN = 0.30
THRESHOLD_MAX = 0.45
THRESHOLD_STEP = 0.05
FAIL_RATIO_LIMIT = 0.50  # > 50% failures triggers tuning


def uniform_weights() -> dict[str, float]:
    keys = list(DEFAULT_WEIGHTS.keys())
    val = 1.0 / len(keys)
    return {k: val for k in keys}


def score_text(text: str, weights: dict[str, float] | None = None) -> dict:
    weights = weights or DEFAULT_WEIGHTS
    metrics = {name: km.METRIC_FUNCS[name](text) for name in weights}
    ai_score = sum(weights[k] * metrics[k] for k in weights)
    return {
        "ai_score": ai_score,
        "metrics": metrics,
        "weights": dict(weights),
    }


def verdict(ai_score: float, threshold: float = DEFAULT_THRESHOLD) -> str:
    return "BLOCKED" if ai_score > threshold else "PASS"


@dataclass(frozen=True)
class TuneResult:
    weights: dict[str, float]
    threshold: float
    action: str  # "no_change" | "threshold_up" | "weights_reset"

    def __eq__(self, other):
        if not isinstance(other, TuneResult):
            return NotImplemented
        return (
            self.weights == other.weights
            and abs(self.threshold - other.threshold) < 1e-9
            and self.action == other.action
        )


def tune(
    scores: Sequence[float],
    weights: dict[str, float],
    threshold: float,
) -> TuneResult:
    """Deterministic threshold/weight auto-tuner (S3).

    Rule:
      1. If fail_ratio > 0.50, attempt to relax the threshold by +0.05 (cap at THRESHOLD_MAX).
      2. If threshold cannot be relaxed (already at cap), reset weights to uniform.
      3. Otherwise no change.
    """
    if not scores:
        return TuneResult(weights=dict(weights), threshold=threshold, action="no_change")
    fails = sum(1 for s in scores if s > threshold)
    fail_ratio = fails / len(scores)
    if fail_ratio <= FAIL_RATIO_LIMIT:
        return TuneResult(weights=dict(weights), threshold=threshold, action="no_change")
    # "1회 자동 조정 + 그래도 fail > 50%면 reset" (PRD §3 D6).
    # The single bump is available only when threshold is still at the default.
    # If threshold already shifted upward (round-1 bump applied), go straight to reset.
    bumped = round(threshold + THRESHOLD_STEP, 4)
    if abs(threshold - DEFAULT_THRESHOLD) < 1e-9 and bumped <= THRESHOLD_MAX + 1e-9:
        return TuneResult(weights=dict(weights), threshold=bumped, action="threshold_up")
    return TuneResult(weights=uniform_weights(), threshold=threshold, action="weights_reset")


# --- CLI -------------------------------------------------------------------

def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path", help="markdown file to score")
    ap.add_argument("--threshold", type=float, default=DEFAULT_THRESHOLD)
    ap.add_argument("--json", action="store_true", help="emit machine-readable report")
    args = ap.parse_args(argv)

    text = Path(args.path).read_text()
    result = score_text(text)
    v = verdict(result["ai_score"], args.threshold)
    payload = {
        "path": args.path,
        "ai_score": result["ai_score"],
        "threshold": args.threshold,
        "verdict": v,
        "metrics": result["metrics"],
        "weights": result["weights"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"copy-killer {v} ai_score={result['ai_score']:.3f} threshold={args.threshold:.2f}")
        for k, val in result["metrics"].items():
            print(f"  {k}: {val:.3f}  (w={result['weights'][k]:.2f})")
    return 0 if v == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
