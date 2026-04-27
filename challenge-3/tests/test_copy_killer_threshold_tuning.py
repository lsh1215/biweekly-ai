"""S3 — threshold auto-tuning rule (deterministic, no LLM).

Rule (PRD §3 D6):
  1. If fail_ratio > 0.5 at default threshold 0.35, bump threshold by ±0.05 once
     within bounds [0.30, 0.45]. Direction: up (relax) when too many fail.
  2. If fail_ratio > 0.5 still, reset weights to uniform 1/6.
  3. Otherwise no change.

The tuner takes a list of pre-computed ai_score floats and current weights/threshold
and returns a *new* tuner state. Pure function. Same inputs → same outputs.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer  # type: ignore


def test_no_tuning_when_fail_ratio_at_or_below_half():
    # 8 of 16 fail (50% exactly is NOT > 50%, so no change).
    scores = [0.50] * 8 + [0.10] * 8
    result = copy_killer.tune(scores, weights=copy_killer.DEFAULT_WEIGHTS,
                              threshold=copy_killer.DEFAULT_THRESHOLD)
    assert result.threshold == 0.35
    assert result.weights == copy_killer.DEFAULT_WEIGHTS
    assert result.action == "no_change"


def test_first_tune_relaxes_threshold_by_0_05():
    # 12 of 16 fail at 0.35 -> bump threshold to 0.40 (relax).
    scores = [0.50] * 12 + [0.10] * 4
    result = copy_killer.tune(scores, weights=copy_killer.DEFAULT_WEIGHTS,
                              threshold=copy_killer.DEFAULT_THRESHOLD)
    assert abs(result.threshold - 0.40) < 1e-9
    assert result.weights == copy_killer.DEFAULT_WEIGHTS
    assert result.action == "threshold_up"


def test_second_round_resets_weights_when_still_failing():
    # already bumped to 0.40; still fail > 50% -> uniform reset.
    scores = [0.55] * 12 + [0.10] * 4
    result = copy_killer.tune(scores, weights=copy_killer.DEFAULT_WEIGHTS,
                              threshold=0.40)
    expected_uniform = copy_killer.uniform_weights()
    assert result.weights == expected_uniform
    assert result.action == "weights_reset"


def test_tuner_is_deterministic():
    scores = [0.6, 0.4, 0.5, 0.7, 0.3, 0.8, 0.2, 0.65, 0.55, 0.45, 0.5, 0.6, 0.7, 0.4, 0.5, 0.55]
    a = copy_killer.tune(scores, weights=copy_killer.DEFAULT_WEIGHTS,
                         threshold=copy_killer.DEFAULT_THRESHOLD)
    b = copy_killer.tune(scores, weights=copy_killer.DEFAULT_WEIGHTS,
                        threshold=copy_killer.DEFAULT_THRESHOLD)
    assert a == b


def test_threshold_does_not_exceed_max():
    # Even if scores look high, the bump cannot push threshold over 0.45.
    scores = [0.99] * 16
    # start already at 0.45 — bumping further would violate cap.
    result = copy_killer.tune(scores, weights=copy_killer.DEFAULT_WEIGHTS,
                              threshold=0.45)
    # cannot bump up; should fall through to weights_reset.
    assert result.action == "weights_reset"
    assert result.threshold == 0.45
