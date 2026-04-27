"""Smoke test for run_sprint2_pipeline.run_one and report shape.

Does NOT require all 16 critic replays to be present - skips per-fixture if
the critic JSON is missing (the field stays as `MISSING`).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import run_sprint2_pipeline as pipe  # type: ignore


@pytest.fixture(autouse=True)
def reset_outputs():
    out = pipe.SPRINT2_OUT
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True, exist_ok=True)
    yield
    # leave outputs for inspection


def test_run_one_emits_md_and_report_for_blog_kafka():
    pairs = pipe.list_fixtures()
    assert (
        ("blog", "kafka-eos") in pairs
    ), "blog/kafka-eos fixture missing - sprint 0/1 setup is broken"
    report = pipe.run_one("blog", "kafka-eos")
    assert report["format"] == "blog"
    assert report["slug"] == "kafka-eos"
    md = pipe.SPRINT2_OUT / "blog-kafka-eos.md"
    rj = pipe.SPRINT2_OUT / "blog-kafka-eos.report.json"
    assert md.is_file() and md.stat().st_size > 0
    assert rj.is_file()
    parsed = json.loads(rj.read_text())
    assert parsed["copy_killer"]["verdict"] in ("PASS", "BLOCKED")
    assert parsed["scrubber"]["verdict"] in ("PASS", "NEEDS_HUMAN_REVIEW", "BLOCKED")
    assert parsed["structure_critic"]["verdict"] in ("APPROVE", "ITERATE", "REJECT", "MISSING")


def test_report_shape_keys():
    report = pipe.run_one("blog", "kafka-eos")
    expected_top = {"format", "slug", "scrubber", "copy_killer", "structure_critic"}
    assert expected_top <= set(report.keys())
    assert {"applied", "residual_matches", "verdict", "notes"} <= set(report["scrubber"].keys())
    assert {"ai_score", "verdict", "threshold", "metrics", "weights"} <= set(report["copy_killer"].keys())
    assert {"verdict"} <= set(report["structure_critic"].keys())
    metrics = report["copy_killer"]["metrics"]
    assert set(metrics.keys()) == {
        "sentence_length_variance",
        "avg_syllable_length",
        "connector_frequency",
        "r1_r7_residual",
        "monotone_ending_ratio",
        "generic_modifier_density",
    }
