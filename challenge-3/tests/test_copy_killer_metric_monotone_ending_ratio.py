"""Metric — monotone_ending_ratio.

4문장 연속 동일 어미 발생 횟수 / 총 문장 수.
Detects long runs of identical sentence endings (e.g., "~다.", "~다.", "~다.", "~다.").
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer_metrics as m  # type: ignore


def test_varied_endings_scores_zero():
    text = "측정했다. 결과가 좋았는가? 그렇다고 본다. 다만 한계도 있고."
    score = m.monotone_ending_ratio(text)
    assert score == 0.0


def test_four_consecutive_da_ending_counts():
    text = "측정했다. 적용했다. 검증했다. 기록했다."
    score = m.monotone_ending_ratio(text)
    assert score > 0.0


def test_three_consecutive_does_not_count():
    text = "측정했다. 적용했다. 검증했다. 기록했어요."
    score = m.monotone_ending_ratio(text)
    assert score == 0.0


def test_score_in_range():
    text = ("측정했다. 적용했다. 검증했다. 기록했다. 발표했다. 정리했다. 공유했다. 마쳤다.")
    score = m.monotone_ending_ratio(text)
    assert 0.0 <= score <= 1.0


def test_empty_returns_zero():
    assert m.monotone_ending_ratio("") == 0.0
