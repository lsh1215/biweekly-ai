"""Sprint-2 only: live capture of structure-critic replies for 16 fixtures.

Order per fixture:
  1. `claude -p --output-format json --model claude-opus-4-7` subprocess.
  2. On auth fail (keychain/401/unauthor) → write `.half_scope=auth_locked` and abort.

Auto recapture is forbidden after this single sprint-2 run (D7).
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path

import critic_replay as cr
import replay_common as rc

CLI_TIMEOUT_SECS = 300
CRITIC_MODEL = "claude-opus-4-5"


def call_claude_cli(system: str, user: str, model: str = CRITIC_MODEL) -> dict:
    cmd = [
        "claude", "-p", user,
        "--output-format", "json",
        "--model", model,
        "--append-system-prompt", system,
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=CLI_TIMEOUT_SECS)
    stderr = (proc.stderr or "").lower()
    if proc.returncode != 0 or "keychain" in stderr or "401" in stderr or "unauthor" in stderr:
        raise RuntimeError(f"claude CLI failed: rc={proc.returncode} stderr={proc.stderr[:200]}")
    try:
        data = json.loads(proc.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"claude CLI returned non-JSON: {e}; head={proc.stdout[:200]}")
    text = ""
    if isinstance(data, dict):
        if "result" in data and isinstance(data["result"], str):
            text = data["result"]
        elif "content" in data and isinstance(data["content"], list):
            for b in data["content"]:
                if isinstance(b, dict) and b.get("type") == "text":
                    text += b.get("text", "")
    if not text:
        raise RuntimeError(f"claude CLI returned empty text")
    return {
        "stop_reason": data.get("stop_reason", "end_turn"),
        "content": [{"type": "text", "text": text}],
    }


def capture_one(fmt: str, slug: str, mode: str = "live", synth_text: str | None = None) -> Path:
    draft_path = rc.SPRINT1_OUT / f"{fmt}-{slug}.md"
    if not draft_path.is_file():
        raise FileNotFoundError(draft_path)
    draft_text = draft_path.read_text()
    request = cr.build_critic_request(fmt, slug, draft_text)
    dispatch_key = rc.compute_dispatch_key(request["messages"])

    if mode == "live":
        response = call_claude_cli(request["system"], request["messages"][0]["content"])
        model = CRITIC_MODEL
    elif mode == "synth":
        if synth_text is None:
            raise RuntimeError("synth requires synth_text")
        response = {"stop_reason": "end_turn",
                    "content": [{"type": "text", "text": synth_text}]}
        model = "synth-claude-opus-4-7"
    else:
        raise ValueError(mode)

    payload = {
        "model": model,
        "captured_at": rc.now_iso(),
        "stage": cr.CRITIC_STAGE,
        "request": request,
        "response": response,
        "dispatch_key": dispatch_key,
        "format": fmt,
    }
    out = cr.critic_replay_path(fmt, slug)
    rc.write_fixture_json(out, payload)
    return out


def list_all_pairs() -> list[tuple[str, str]]:
    pairs = []
    for fp in rc.list_all_fixtures():
        f = rc.load_yaml_fixture(fp)
        pairs.append((f["format"], f["slug"]))
    return pairs


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", choices=["live", "synth"], default="live")
    ap.add_argument("--format", help="single fixture format (synth mode only)")
    ap.add_argument("--slug", help="single fixture slug (synth mode only)")
    ap.add_argument("--all", action="store_true", help="capture all 16 fixtures (live)")
    args = ap.parse_args()

    if args.source == "synth":
        if not (args.format and args.slug):
            print("ERR: synth mode requires --format and --slug", file=sys.stderr)
            return 2
        text = sys.stdin.read()
        if not text.strip():
            print("ERR: synth mode requires verdict block on stdin", file=sys.stderr)
            return 2
        out = capture_one(args.format, args.slug, "synth", synth_text=text)
        print(f"WROTE {out}")
        return 0

    if not args.all:
        print("ERR: --all required for live mode", file=sys.stderr)
        return 2

    pairs = list_all_pairs()
    if len(pairs) != 16:
        print(f"ERR: expected 16 fixtures, found {len(pairs)}", file=sys.stderr)
        return 3

    half_scope = rc.ROOT / ".half_scope"
    captured = 0
    for idx, (fmt, slug) in enumerate(pairs, start=1):
        target = cr.critic_replay_path(fmt, slug)
        if target.exists():
            captured += 1
            print(f"[{captured}/16] CACHED {target.name}")
            continue
        last_err = None
        for attempt in (1, 2):
            try:
                out = capture_one(fmt, slug, "live")
                captured += 1
                print(f"[{captured}/16] LIVE {out.name}")
                break
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                if any(s in err_str for s in ("keychain", "401", "unauthor")):
                    half_scope.write_text("auth_locked")
                    print(f"S5 auth_locked at {fmt}/{slug}: {e}", file=sys.stderr)
                    return 5
                if attempt == 1:
                    print(f"  retry {fmt}/{slug}: {e}", file=sys.stderr)
                    time.sleep(3.0)
                    continue
                print(f"  SKIP {fmt}/{slug}: {e}", file=sys.stderr)
        time.sleep(1.0)

    print(f"DONE {captured}/16 captured")
    return 0 if captured == 16 else 6


if __name__ == "__main__":
    sys.exit(main())
