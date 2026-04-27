"""Metric — r1_r7_residual.

scrubber 후 R1~R7 grep matches. Higher = more residual = more AI tells.
Detects residual em-dash, en-dash, anthropomorphism, drama verbs, meta-closings,
thesis prefixes, future-tense markers. All non-code-block scope.
"""
from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import copy_killer_metrics as m  # type: ignore


def test_clean_text_returns_zero():
    text = "측정 결과는 명확했다. 적용 후 중복률은 0%로 떨어졌다."
    score = m.r1_r7_residual(text)
    assert score == 0.0


def test_em_dash_outside_code_counts():
    text = "EOS 의 비용 — latency 증가 — 는 받아들였다."
    score = m.r1_r7_residual(text)
    assert score > 0.0


def test_em_dash_inside_code_block_does_not_count():
    text = "정상 문장이다.\n\n```\nlogger output — error\n```\n\n또 다른 정상 문장."
    score = m.r1_r7_residual(text)
    assert score == 0.0


def test_drama_verb_counts():
    text = "결제가 증발했다."
    score = m.r1_r7_residual(text)
    assert score > 0.0


def test_thesis_label_counts():
    text = "**Thesis.** 지연은 실패다."
    score = m.r1_r7_residual(text)
    assert score > 0.0


def test_meta_closing_counts():
    text = "이게 EOS 다."
    score = m.r1_r7_residual(text)
    assert score > 0.0


def test_score_capped_at_one():
    # Many violations should saturate to 1.0, not exceed it.
    text = ("증발했다 — 신경 쓰지 않는다 — 운명을 공유 — 숨을 쉰다 — "
            "악질인 이유 — 이게 EOS 다 — 한 일은 그뿐 — 이것이 전부 — ") * 5
    score = m.r1_r7_residual(text)
    assert 0.0 <= score <= 1.0
