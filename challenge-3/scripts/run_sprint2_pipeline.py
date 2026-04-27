"""Sprint-2 pipeline runner.

For each of the 16 fixtures:
  1. Read sprint1 writer output (markdown).
  2. Run deterministic Python scrubber (R1-R7 + per-format extras).
  3. Run copy-killer (6 indicators, weighted score, threshold compare).
  4. Load structure-critic replay JSON and parse the verdict.
  5. Write the scrubbed .md and a {fmt}-{slug}.report.json with all of:
     - scrubber summary
     - copy_killer score / verdict / metrics
     - structure_critic verdict + raw text snippet

S3 auto-tune: after the first pass, if fail_ratio > 0.5 the threshold is
bumped by +0.05 and a second pass replaces only the verdict (the metrics do not
change). If still failing, weights are reset to uniform and a third pass is
done. All adjustments are logged to TIMELINE via stdout (the checkpoint pipes
this to TIMELINE.md).

Idempotent: clears `fixtures/outputs/sprint2/` on entry.
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import copy_killer as ck
import critic_replay as cr
import replay_common as rc
import scrubber as sc

ROOT = rc.ROOT
SPRINT2_OUT = ROOT / "fixtures" / "outputs" / "sprint2"


def list_fixtures() -> list[tuple[str, str]]:
    pairs = []
    for fp in rc.list_all_fixtures():
        f = rc.load_yaml_fixture(fp)
        pairs.append((f["format"], f["slug"]))
    return pairs


def run_one(fmt: str, slug: str) -> dict:
    sprint1_path = rc.SPRINT1_OUT / f"{fmt}-{slug}.md"
    if not sprint1_path.is_file():
        raise FileNotFoundError(f"sprint1 draft missing: {sprint1_path}")
    text = sprint1_path.read_text()

    scrubbed_text, scrub_report = sc.scrub(text, fmt)

    score_result = ck.score_text(scrubbed_text)
    verdict = ck.verdict(score_result["ai_score"], ck.DEFAULT_THRESHOLD)

    out_md = SPRINT2_OUT / f"{fmt}-{slug}.md"
    out_md.write_text(scrubbed_text)

    critic_path = cr.critic_replay_path(fmt, slug)
    critic_payload: dict = {"verdict": "MISSING", "model": None, "snippet": ""}
    if critic_path.is_file():
        d = json.loads(critic_path.read_text())
        text_resp = rc.extract_response_text(d["response"])
        critic_payload = {
            "verdict": cr.parse_verdict(text_resp),
            "model": d.get("model"),
            "snippet": text_resp.strip().splitlines()[:6],
            "captured_at": d.get("captured_at"),
        }

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
            "verdict": verdict,
            "threshold": ck.DEFAULT_THRESHOLD,
            "metrics": score_result["metrics"],
            "weights": score_result["weights"],
        },
        "structure_critic": critic_payload,
    }
    out_json = SPRINT2_OUT / f"{fmt}-{slug}.report.json"
    out_json.write_text(json.dumps(report, ensure_ascii=False, indent=2))
    return report


def auto_tune_pass(reports: list[dict]) -> dict | None:
    """Apply S3 auto-tune at the 16-fixture level.

    Returns a dict {action, threshold, weights} if a tune was applied, else None.
    Updates the in-place `copy_killer.verdict` of each report when threshold/weights change.
    """
    scores = [r["copy_killer"]["ai_score"] for r in reports]
    weights = ck.DEFAULT_WEIGHTS
    threshold = ck.DEFAULT_THRESHOLD
    history = []
    for round_idx in (1, 2):
        result = ck.tune(scores, weights, threshold)
        if result.action == "no_change":
            break
        history.append({
            "round": round_idx,
            "action": result.action,
            "threshold": result.threshold,
            "weights": result.weights,
        })
        # Recompute scores under new weights if reset
        if result.action == "weights_reset":
            for r in reports:
                metrics = r["copy_killer"]["metrics"]
                new_score = sum(result.weights[k] * metrics[k] for k in metrics)
                r["copy_killer"]["ai_score"] = new_score
                r["copy_killer"]["weights"] = dict(result.weights)
            scores = [r["copy_killer"]["ai_score"] for r in reports]
        threshold = result.threshold
        weights = result.weights
        # Update verdicts under the new threshold/weights
        for r in reports:
            r["copy_killer"]["threshold"] = threshold
            r["copy_killer"]["verdict"] = ck.verdict(r["copy_killer"]["ai_score"], threshold)
    if not history:
        return None
    return {"history": history, "final_threshold": threshold, "final_weights": weights}


def main() -> int:
    if SPRINT2_OUT.exists():
        shutil.rmtree(SPRINT2_OUT)
    SPRINT2_OUT.mkdir(parents=True, exist_ok=True)

    pairs = list_fixtures()
    if len(pairs) != 16:
        print(f"ERR: expected 16 fixtures, got {len(pairs)}", file=sys.stderr)
        return 3

    reports: list[dict] = []
    for fmt, slug in pairs:
        try:
            r = run_one(fmt, slug)
            reports.append(r)
            verdict = r["copy_killer"]["verdict"]
            ai_score = r["copy_killer"]["ai_score"]
            critic = r["structure_critic"]["verdict"]
            print(f"  {fmt}/{slug}: copy={verdict} ai={ai_score:.3f} critic={critic}")
        except Exception as e:
            print(f"  FAIL {fmt}/{slug}: {e}", file=sys.stderr)
            return 4

    tune_history = auto_tune_pass(reports)
    if tune_history:
        print(f"S3 auto-tune applied: {json.dumps(tune_history, ensure_ascii=False)}")
        # Re-write report jsons with updated verdicts/threshold
        for r in reports:
            out_json = SPRINT2_OUT / f"{r['format']}-{r['slug']}.report.json"
            out_json.write_text(json.dumps(r, ensure_ascii=False, indent=2))

    # Summary line for TIMELINE
    fails = sum(1 for r in reports if r["copy_killer"]["verdict"] == "BLOCKED")
    rejects = sum(1 for r in reports
                  if r["structure_critic"]["verdict"] == "REJECT")
    iterates = sum(1 for r in reports
                   if r["structure_critic"]["verdict"] == "ITERATE")
    approves = sum(1 for r in reports
                   if r["structure_critic"]["verdict"] == "APPROVE")
    threshold = reports[0]["copy_killer"]["threshold"] if reports else 0
    print(
        f"SUMMARY copy_killer_blocked={fails}/16 threshold={threshold:.2f} "
        f"critic APPROVE={approves} ITERATE={iterates} REJECT={rejects}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
