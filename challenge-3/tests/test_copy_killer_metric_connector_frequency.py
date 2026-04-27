"""Metric — connector_frequency.

그러나/하지만/따라서/즉/또한 occurrences per 1000 chars, then normalized.
Heavy connector use is an AI tell.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer_metrics as m  # type: ignore


def test_no_connectors_scores_zero():
    text = "측정 결과 p99 latency는 47ms에서 62ms로 증가했다. 이 비용은 받아들였다."
    score = m.connector_frequency(text)
    assert score == 0.0


def test_dense_connectors_score_high():
    text = ("그러나 측정 결과는 다르다. 하지만 우리는 그 비용을 받아들였다. "
            "따라서 EOS를 적용했다. 즉, throughput 손실을 감수한다. "
            "또한 transaction coordinator 부하도 늘어난다. 그러나 안전이 우선이다.") * 2
    score = m.connector_frequency(text)
    assert 0.0 <= score <= 1.0
    assert score >= 0.5


def test_empty_returns_zero():
    assert m.connector_frequency("") == 0.0
