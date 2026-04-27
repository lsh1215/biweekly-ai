"""Metric — sentence_length_variance.

std/mean of sentence char length, then squashed into [0,1].
Higher score = more uniform sentence lengths (an AI tell).
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer_metrics as m  # type: ignore


def test_uniform_sentence_lengths_score_high():
    text = "이 문장은 길이가 같다. 두번째 문장도 비슷하다. 세번째도 마찬가지. 네번째도 유사함."
    score = m.sentence_length_variance(text)
    assert 0.0 <= score <= 1.0
    # uniform sentences -> low std/mean -> score near 1.0 (more AI-like)
    assert score >= 0.7, f"uniform-length got {score}"


def test_varied_sentence_lengths_score_low():
    text = (
        "짧다. "
        "조금 더 긴 두 번째 문장이다. "
        "이것은 훨씬 더 길게 늘어진 세 번째 문장으로, 여러 절을 포함하고 자연스럽게 호흡을 늘려 나간다. "
        "또 짧다."
    )
    score = m.sentence_length_variance(text)
    assert 0.0 <= score <= 1.0
    assert score <= 0.4, f"varied-length got {score}"


def test_empty_text_returns_zero():
    assert m.sentence_length_variance("") == 0.0


def test_single_sentence_returns_zero():
    assert m.sentence_length_variance("한 문장만 있다.") == 0.0
