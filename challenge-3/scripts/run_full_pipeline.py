"""Sprint-3 full pipeline runner: 16 fixture × 4 deterministic stage.

Stages (per fixture):
  1. writer-replay   - load replay/fixtures/{fmt}/{slug}-writer.json,
                       verify dispatch_key, write fixtures/outputs/sprint3/{fmt}-{slug}.md
  2. scrubber        - Python scrubber.scrub() on the .md
  3. copy-killer     - Python copy_killer.score_text() + threshold compare
  4. fact-checker    - fact_checker.check() against known_facts.yml.example

structure-critic verdict is taken from sprint-1 critic replay JSON (D11
deterministic via replay) and stored in the report; the run does NOT
re-evaluate the critic.

Output:
  fixtures/outputs/sprint3/{fmt}-{slug}.md           (16, scrubbed)
  fixtures/outputs/sprint3/{fmt}-{slug}.report.json  (16, 4 stages + critic)

Idempotent (CLAUDE.md §10).
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import copy_killer as ck
import critic_replay as cr
import fact_checker as fc
import replay_common as rc
import scrubber as sc

ROOT = rc.ROOT
SPRINT3_OUT = ROOT / "fixtures" / "outputs" / "sprint3"
KNOWN_FACTS = ROOT / "known_facts.yml.example"


def list_fixtures() -> list[tuple[str, str, dict]]:
    pairs = []
    for fp in rc.list_all_fixtures():
        f = rc.load_yaml_fixture(fp)
        pairs.append((f["format"], f["slug"], f))
    return pairs


def run_one(fmt: str, slug: str, yaml_data: dict) -> dict:
    """Execute the 4 deterministic stages for a single fixture."""
    # Stage 1: writer-replay
    replay_path = rc.fixture_replay_path(fmt, slug, "writer")
    if not replay_path.is_file():
        raise FileNotFoundError(f"writer replay missing: {replay_path}")
    payload = rc.read_fixture_json(replay_path)
    raw_text = rc.extract_response_text(payload["response"])
    draft_text = rc.clean_draft_markdown(raw_text)

    # Stage 2: scrubber
    scrubbed_text, scrub_report = sc.scrub(draft_text, fmt)

    # Stage 3: copy-killer
    score_result = ck.score_text(scrubbed_text)
    ck_verdict = ck.verdict(score_result["ai_score"], ck.DEFAULT_THRESHOLD)

    # Stage 4: fact-checker
    fc_result = fc.check(scrubbed_text, yaml_data)

    # Critic verdict from replay (deterministic via D11 replay)
    critic_path = cr.critic_replay_path(fmt, slug)
    critic_payload: dict = {"verdict": "MISSING", "model": None, "snippet": ""}
    if critic_path.is_file():
        d = json.loads(critic_path.read_text())
        text_resp = rc.extract_response_text(d["response"])
        critic_payload = {
            "verdict": cr.parse_verdict(text_resp),
            "model": d.get("model"),
            "captured_at": d.get("captured_at"),
        }

    # Write artifacts
    out_md = SPRINT3_OUT / f"{fmt}-{slug}.md"
    out_md.write_text(scrubbed_text, encoding="utf-8")

    report = {
        "format": fmt,
        "slug": slug,
        "scrubber": {
            "applied": scrub_report.applied,
            "residual_matches": scrub_report.residual_matches,
            "verdict": scrub_report.verdict,
            "notes": scrub_report.notes,
        },
        "copy_killer": {
            "ai_score": score_result["ai_score"],
            "verdict": ck_verdict,
            "threshold": ck.DEFAULT_THRESHOLD,
            "metrics": score_result["metrics"],
            "weights": score_result["weights"],
        },
        "fact_checker": {
            "verdict": fc_result["verdict"],
            "summary": fc_result["summary"],
            "unknowns": fc_result["unknowns"],
        },
        "structure_critic": critic_payload,
    }
    (SPRINT3_OUT / f"{fmt}-{slug}.report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    return report


def main() -> int:
    if SPRINT3_OUT.exists():
        shutil.rmtree(SPRINT3_OUT)
    SPRINT3_OUT.mkdir(parents=True, exist_ok=True)

    yaml_data = fc.load_yaml(KNOWN_FACTS)
    pairs = list_fixtures()
    if len(pairs) != 16:
        print(f"ERR: expected 16 fixtures, got {len(pairs)}", file=sys.stderr)
        return 3

    reports: list[dict] = []
    for fmt, slug, _ in pairs:
        try:
            r = run_one(fmt, slug, yaml_data)
            reports.append(r)
            print(
                f"  {fmt}/{slug}: "
                f"scrub={r['scrubber']['verdict']} "
                f"ck={r['copy_killer']['verdict']} ai={r['copy_killer']['ai_score']:.3f} "
                f"fc={r['fact_checker']['verdict']} "
                f"critic={r['structure_critic']['verdict']}"
            )
        except Exception as e:
            print(f"  FAIL {fmt}/{slug}: {e}", file=sys.stderr)
            return 4

    rejects = sum(1 for r in reports if r["structure_critic"]["verdict"] == "REJECT")
    blocks_ck = sum(1 for r in reports if r["copy_killer"]["verdict"] == "BLOCKED")
    blocks_fc = sum(1 for r in reports if r["fact_checker"]["verdict"] == "BLOCKED")
    print(
        f"SUMMARY 16/16 rejects={rejects} ck_blocked={blocks_ck} fc_blocked={blocks_fc}"
    )
    if rejects:
        print(f"ERR: structure_critic REJECT count must be 0 (got {rejects})", file=sys.stderr)
        return 5
    return 0


if __name__ == "__main__":
    sys.exit(main())
