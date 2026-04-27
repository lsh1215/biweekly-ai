"""Live recording: 16 fixtures × writer call → JSON saved to replay/fixtures/.

Sprint 1 only. Recapture is gated by scripts/recapture_replay.sh (manual).
Auto recapture is forbidden (D7 lock).

Order of attempts per fixture:
  1. `claude -p --output-format json --model claude-sonnet-4-5` subprocess.
     Detects S5 (keychain prompt / 401) via stderr / non-zero exit.
  2. On S5 / S4 (auth fail): write `.half_scope=auth_locked`, abort the run, and
     re-raise so the orchestrator can fall back to the synthesis path.

The synthesis path (`--source synth`) is used by sprint-1 when the agent itself
is acting as the writer (overnight no-keychain context). It writes a
spec-shape JSON whose response.content[0].text is provided via stdin.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import replay_common as rc

CLI_TIMEOUT_SECS = 300


def call_claude_cli(system: str, user: str, model: str = rc.WRITER_MODEL) -> dict:
    """Run `claude -p` and return a parsed response dict, or raise on auth fail."""
    cmd = [
        "claude",
        "-p",
        user,
        "--output-format", "json",
        "--model", model,
        "--append-system-prompt", system,
    ]
    proc = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=CLI_TIMEOUT_SECS,
    )
    stderr = (proc.stderr or "").lower()
    if proc.returncode != 0 or "keychain" in stderr or "401" in stderr or "unauthor" in stderr:
        raise RuntimeError(f"claude CLI failed: rc={proc.returncode} stderr={proc.stderr[:200]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude CLI returned non-JSON output: {e}; head={proc.stdout[:200]}")
    text = ""
    if isinstance(data, dict):
        if "result" in data and isinstance(data["result"], str):
            text = data["result"]
        elif "content" in data and isinstance(data["content"], list):
            for b in data["content"]:
                if isinstance(b, dict) and b.get("type") == "text":
                    text += b.get("text", "")
    if not text:
        raise RuntimeError(f"claude CLI returned empty text: keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
    return {
        "stop_reason": data.get("stop_reason", "end_turn"),
        "content": [{"type": "text", "text": text}],
    }


def capture_one(fixture_path: Path, mode: str, synth_text: str | None = None) -> Path:
    fixture = rc.load_yaml_fixture(fixture_path)
    fmt = fixture["format"]
    slug = fixture["slug"]
    request = rc.build_request(fixture)
    dispatch_key = rc.compute_dispatch_key(request["messages"])

    if mode == "live":
        response = call_claude_cli(request["system"], request["messages"][0]["content"])
        model = rc.WRITER_MODEL
    elif mode == "synth":
        if not synth_text:
            raise RuntimeError("synth mode requires synth_text")
        response = {"stop_reason": "end_turn", "content": [{"type": "text", "text": synth_text}]}
        model = "synth-claude-opus-4-7"  # marker: not a live model id
    else:
        raise ValueError(f"unknown mode: {mode}")

    payload = {
        "model": model,
        "captured_at": rc.now_iso(),
        "stage": "writer",
        "request": request,
        "response": response,
        "dispatch_key": dispatch_key,
        "format": fmt,
    }
    out = rc.fixture_replay_path(fmt, slug, "writer")
    rc.write_fixture_json(out, payload)
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["live", "synth"], default="live",
                    help="live: spawn claude CLI; synth: read text from stdin (one fixture only)")
    ap.add_argument("--fixture", help="path to a single fixture yml (synth mode requires this)")
    ap.add_argument("--all", action="store_true", help="capture all 16 fixtures (live only)")
    args = ap.parse_args()

    if args.source == "synth":
        if not args.fixture:
            print("ERR: synth mode requires --fixture", file=sys.stderr)
            return 2
        text = sys.stdin.read()
        if not text.strip():
            print("ERR: synth mode requires draft markdown on stdin", file=sys.stderr)
            return 2
        out = capture_one(Path(args.fixture), "synth", synth_text=text)
        print(f"WROTE {out}")
        return 0

    if not args.all:
        print("ERR: --all required for live mode (or pick --source synth)", file=sys.stderr)
        return 2

    fixtures = rc.list_all_fixtures()
    if len(fixtures) != 16:
        print(f"ERR: expected 16 fixtures, found {len(fixtures)}", file=sys.stderr)
        return 3

    half_scope = rc.ROOT / ".half_scope"
    captured = 0
    auth_failed_first = False
    for idx, fp in enumerate(fixtures):
        target = rc.fixture_replay_path(rc.load_yaml_fixture(fp)["format"], rc.load_yaml_fixture(fp)["slug"], "writer")
        if target.exists():
            captured += 1
            print(f"[{captured}/16] CACHED {target.name}")
            continue
        last_err = None
        for attempt in (1, 2):
            try:
                out = capture_one(fp, "live")
                captured += 1
                print(f"[{captured}/16] LIVE {out.name}")
                break
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                # S5 auth fail signature: keychain / 401 / unauthor
                if any(s in err_str for s in ("keychain", "401", "unauthor")):
                    half_scope.write_text("auth_locked")
                    print(f"S5 auth_locked at fixture {fp.name}: {e}", file=sys.stderr)
                    return 5
                if attempt == 1:
                    print(f"  retry {fp.name}: {e}", file=sys.stderr)
                    time.sleep(3.0)
                    continue
                # final failure: skip this fixture (synth path will fill it in)
                print(f"  SKIP {fp.name} after retries: {e}", file=sys.stderr)
                if idx == 0:
                    auth_failed_first = True
        time.sleep(1.0)

    if auth_failed_first and captured == 0:
        half_scope.write_text("auth_locked")
        return 5

    print(f"DONE {captured}/16 captured")
    return 0 if captured == 16 else 6


if __name__ == "__main__":
    sys.exit(main())
