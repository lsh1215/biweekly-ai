"""D6 — copy-killer weight & threshold lock.

Weights must sum to exactly 1.0; default threshold must be 0.35.
The threshold tuner (S3 fix) bumps in ±0.05 steps within [0.30, 0.45].
A weight reset must produce uniform 1/6 across all six indicators.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer  # type: ignore


def test_six_weights_sum_to_one():
    weights = copy_killer.DEFAULT_WEIGHTS
    assert set(weights.keys()) == {
        "sentence_length_variance",
        "avg_syllable_length",
        "connector_frequency",
        "r1_r7_residual",
        "monotone_ending_ratio",
        "generic_modifier_density",
    }
    total = sum(weights.values())
    assert abs(total - 1.0) < 1e-9, f"weights sum {total} != 1.0"


def test_individual_weight_values_match_prd_d6():
    w = copy_killer.DEFAULT_WEIGHTS
    assert w["sentence_length_variance"] == 0.20
    assert w["avg_syllable_length"] == 0.10
    assert w["connector_frequency"] == 0.20
    assert w["r1_r7_residual"] == 0.30
    assert w["monotone_ending_ratio"] == 0.15
    assert w["generic_modifier_density"] == 0.05


def test_default_threshold_is_zero_point_three_five():
    assert copy_killer.DEFAULT_THRESHOLD == 0.35


def test_uniform_reset_produces_one_sixth_each():
    uniform = copy_killer.uniform_weights()
    assert len(uniform) == 6
    for v in uniform.values():
        assert abs(v - (1.0 / 6.0)) < 1e-9
    assert abs(sum(uniform.values()) - 1.0) < 1e-9


def test_threshold_bounds_lock():
    # Threshold tuner clamps within [0.30, 0.45] in ±0.05 steps.
    assert copy_killer.THRESHOLD_MIN == 0.30
    assert copy_killer.THRESHOLD_MAX == 0.45
    assert copy_killer.THRESHOLD_STEP == 0.05
