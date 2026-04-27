"""TDD: 16 fixture × 4 deterministic stage E2E.

Stages (deterministic):
  1. writer-replay   (loads stored JSON, no LLM)
  2. scrubber        (Python regex + 1:1 substitution)
  3. copy-killer     (6 indicators → ai_score → verdict)
  4. fact-checker    (5 type regex + yaml diff → BLOCKED list)

structure-critic is replay-driven and tested separately
(test_e2e_replay_critic.py from sprint 2).

Outputs:
  fixtures/outputs/sprint3/{format}-{slug}.md           (16)
  fixtures/outputs/sprint3/{format}-{slug}.report.json  (16)

Hard gates (Sprint 3):
  - 16 .md exist
  - 16 .report.json exist
  - REJECT count = 0 (structure_critic from replay)
  - copy_killer.verdict each ∈ {PASS, BLOCKED}
  - fact_checker.verdict each ∈ {PASS, BLOCKED}
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
SPRINT3_OUT = ROOT / "fixtures" / "outputs" / "sprint3"
SCRIPTS = ROOT / "scripts"


@pytest.fixture(scope="module")
def pipeline_run():
    """Run the full pipeline once for the module."""
    sys.path.insert(0, str(SCRIPTS))
    import run_full_pipeline as rfp
    rc = rfp.main()
    assert rc == 0, "run_full_pipeline.main() returned non-zero"
    return rc


def test_run_full_pipeline_module_loads():
    """Sanity: the module exists and exposes main()."""
    sys.path.insert(0, str(SCRIPTS))
    import run_full_pipeline as rfp
    assert hasattr(rfp, "main")


def test_16_md_outputs(pipeline_run):
    mds = sorted(SPRINT3_OUT.glob("*.md"))
    assert len(mds) == 16, [m.name for m in mds]


def test_16_report_jsons(pipeline_run):
    reports = sorted(SPRINT3_OUT.glob("*.report.json"))
    assert len(reports) == 16


def test_each_report_has_4_stages(pipeline_run):
    for f in sorted(SPRINT3_OUT.glob("*.report.json")):
        data = json.loads(f.read_text())
        for stage in ("scrubber", "copy_killer", "fact_checker", "structure_critic"):
            assert stage in data, f"{f.name}: missing {stage}"


def test_no_reject_verdict(pipeline_run):
    rejects = []
    for f in sorted(SPRINT3_OUT.glob("*.report.json")):
        data = json.loads(f.read_text())
        if data.get("structure_critic", {}).get("verdict") == "REJECT":
            rejects.append(f.name)
    assert rejects == [], f"REJECT count must be 0: {rejects}"


def test_copy_killer_verdict_in_set(pipeline_run):
    for f in sorted(SPRINT3_OUT.glob("*.report.json")):
        data = json.loads(f.read_text())
        v = data["copy_killer"]["verdict"]
        assert v in {"PASS", "BLOCKED"}, f"{f.name}: verdict={v}"


def test_fact_checker_verdict_in_set(pipeline_run):
    for f in sorted(SPRINT3_OUT.glob("*.report.json")):
        data = json.loads(f.read_text())
        v = data["fact_checker"]["verdict"]
        assert v in {"PASS", "BLOCKED"}, f"{f.name}: verdict={v}"


def test_pipeline_idempotent(pipeline_run):
    """Re-running should produce identical .md byte-for-byte."""
    sys.path.insert(0, str(SCRIPTS))
    import run_full_pipeline as rfp
    snapshot = {f.name: f.read_bytes() for f in SPRINT3_OUT.glob("*.md")}
    rc = rfp.main()
    assert rc == 0
    after = {f.name: f.read_bytes() for f in SPRINT3_OUT.glob("*.md")}
    assert snapshot == after, "pipeline not idempotent"
