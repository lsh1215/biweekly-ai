"""Replay loader: read replay/fixtures/{fmt}/{slug}-{stage}.json, verify dispatch_key
matches the current fixture's request, and emit the response text to fixtures/outputs/sprint1/.

If dispatch_key mismatches → write `.half_scope=replay_stale_sprint{N}` and exit non-zero (D7).
Auto recapture is forbidden. Manual recapture lives in scripts/recapture_replay.sh.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import replay_common as rc


def hangul_ratio(text: str) -> float:
    # Sprint-1 autonomous decision: prose-only measurement, threshold 0.5.
    # See replay_common.hangul_prose_ratio docstring + TIMELINE.
    return rc.hangul_prose_ratio(text)


HANGUL_RATIO_FLOOR = 0.20


def replay_one(fixture_path: Path, sprint: int = 1) -> Path:
    fixture = rc.load_yaml_fixture(fixture_path)
    fmt = fixture["format"]
    slug = fixture["slug"]
    expected_key = rc.compute_dispatch_key(rc.build_request(fixture)["messages"])

    json_path = rc.fixture_replay_path(fmt, slug, "writer")
    if not json_path.is_file():
        raise FileNotFoundError(f"replay fixture missing: {json_path}")

    payload = rc.read_fixture_json(json_path)
    if payload["dispatch_key"] != expected_key:
        half = rc.ROOT / ".half_scope"
        half.write_text(f"replay_stale_sprint{sprint}")
        raise RuntimeError(
            f"dispatch_key mismatch for {fmt}/{slug}: stored={payload['dispatch_key'][:12]} "
            f"expected={expected_key[:12]} → .half_scope=replay_stale_sprint{sprint}"
        )

    raw_text = rc.extract_response_text(payload["response"])
    text = rc.clean_draft_markdown(raw_text)
    out = rc.fixture_output_path(fmt, slug)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(text)

    ratio = hangul_ratio(text)
    if ratio < HANGUL_RATIO_FLOOR:
        half = rc.ROOT / ".half_scope"
        half.write_text(f"lang_leak_{fmt}")
        raise RuntimeError(
            f"S6 Hangul prose ratio {ratio:.2f} < {HANGUL_RATIO_FLOOR} for {fmt}/{slug} → .half_scope=lang_leak_{fmt}"
        )
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="replay all 16 fixtures")
    ap.add_argument("--fixture", help="single fixture yml (alternative)")
    ap.add_argument("--sprint", type=int, default=1)
    args = ap.parse_args()

    if args.fixture:
        out = replay_one(Path(args.fixture), sprint=args.sprint)
        print(f"REPLAY {out}")
        return 0

    if not args.all:
        print("ERR: pass --all or --fixture", file=sys.stderr)
        return 2

    fixtures = rc.list_all_fixtures()
    if len(fixtures) != 16:
        print(f"ERR: expected 16 fixtures, found {len(fixtures)}", file=sys.stderr)
        return 3

    out_dir = rc.SPRINT1_OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    # idempotent: clear stale outputs (CLAUDE.md §10)
    for f in out_dir.glob("*.md"):
        f.unlink()

    failed = 0
    for fp in fixtures:
        try:
            out = replay_one(fp, sprint=args.sprint)
            print(f"  OK {out.name}")
        except Exception as e:
            failed += 1
            print(f"  FAIL {fp.name}: {e}", file=sys.stderr)

    if failed:
        return 4
    print(f"DONE 16/16")
    return 0


if __name__ == "__main__":
    sys.exit(main())
