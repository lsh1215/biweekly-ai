"""Metric — generic_modifier_density.

매우/정말/너무/굉장히 occurrences per 1000 chars, normalized.
Generic modifier density is an AI/cliché tell.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer_metrics as m  # type: ignore


def test_no_modifiers_scores_zero():
    text = "측정 결과는 p99 47ms에서 62ms로 늘어났다. throughput은 15% 줄었다."
    score = m.generic_modifier_density(text)
    assert score == 0.0


def test_dense_modifiers_score_high():
    text = ("매우 정말 너무 굉장히 매우 정말 너무 굉장히 매우 정말 너무 굉장히 매우 정말") * 3
    score = m.generic_modifier_density(text)
    assert score > 0.5


def test_empty_returns_zero():
    assert m.generic_modifier_density("") == 0.0
