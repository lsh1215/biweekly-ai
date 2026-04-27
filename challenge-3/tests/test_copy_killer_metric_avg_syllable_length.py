"""Metric — avg_syllable_length.

mean Hangul syllable count per 100 chars, normalized to [0,1].
Higher density of Hangul syllables => higher score.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer_metrics as m  # type: ignore


def test_pure_korean_text_high_density():
    text = "한국어 문장은 한글 음절로만 구성되어 있을 때 음절 밀도가 높다."
    score = m.avg_syllable_length(text)
    assert 0.0 <= score <= 1.0
    assert score >= 0.6


def test_mostly_english_text_low_density():
    text = "Kafka producer idempotence transactional API consumer read_committed offset."
    score = m.avg_syllable_length(text)
    assert score <= 0.2


def test_empty_returns_zero():
    assert m.avg_syllable_length("") == 0.0
