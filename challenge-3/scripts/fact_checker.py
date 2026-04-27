"""fact-checker - LLM-free yaml-diff verifier (PRD §3 D3).

Usage:
  python3 scripts/fact_checker.py <md_path> --known known_facts.yml [--json]

Behavior:
  1. Extract 5 type hard-evidence from the draft body (code blocks stripped).
  2. Diff against the user yaml (numbers / semver / direct_quotes / dates /
     proper_nouns lists).
  3. Anything found in the draft but NOT in the yaml is an "unknown fact" and
     contributes to the BLOCKED set.
  4. Verdict:
     - PASS    when all extracted facts are whitelisted (or yaml absent and
                draft contains no hard-evidence)
     - BLOCKED when at least one "must-evidence" type has unknowns. Numbers /
                semver / dates / quotes are hard. Proper nouns are reported but
                NOT BLOCKING (heuristic noise too high in Korean tech writing).

Exit code 0 = PASS, 1 = BLOCKED, 2 = usage error.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

# Allow running as a script (no package) by importing the sibling module
# either way.
try:
    import fact_checker_patterns as fcp  # type: ignore
except ImportError:  # pragma: no cover - exercised when imported as a module
    from . import fact_checker_patterns as fcp  # type: ignore

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_YAML = ROOT / "known_facts.yml"


def strip_code_blocks(text: str) -> str:
    """Remove fenced ``` blocks and inline `code` for prose-only checking."""
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`[^`\n]+`", "", text)
    return text


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        import yaml
    except ImportError:
        print("ERR: pyyaml not installed (.venv missing dependency?)", file=sys.stderr)
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        return {}
    return data


def _string_list(yaml_data: dict, key: str) -> list[str]:
    val = yaml_data.get(key) or []
    if not isinstance(val, list):
        return []
    return [str(v) for v in val]


def is_whitelisted(token: str, allow: list[str]) -> bool:
    """A token is whitelisted if any allow-entry contains the token, or vice versa.

    The yaml entries are user-authored and may include extra context
    ("p99 47ms"), so substring containment in either direction counts as a hit.
    """
    if not token:
        return True
    t = token.strip()
    if not t:
        return True
    for a in allow:
        a_str = a.strip()
        if not a_str:
            continue
        if t == a_str:
            return True
        if t in a_str:
            return True
        if a_str in t:
            return True
    return False


def diff_unknowns(found: dict[str, list[str]], yaml_data: dict) -> dict[str, list[str]]:
    keys = {
        "numbers": "numbers",
        "semver": "semver",
        "quotes": "direct_quotes",
        "dates": "dates",
        "proper_nouns": "proper_nouns",
    }
    out: dict[str, list[str]] = {}
    for fk, yk in keys.items():
        allow = _string_list(yaml_data, yk)
        unknowns = []
        for tok in found[fk]:
            if not is_whitelisted(tok, allow):
                unknowns.append(tok)
        out[fk] = unknowns
    return out


HARD_KEYS = ("numbers", "semver", "quotes", "dates")


def determine_verdict(unknowns: dict[str, list[str]]) -> str:
    for k in HARD_KEYS:
        if unknowns.get(k):
            return "BLOCKED"
    return "PASS"


def check(text: str, yaml_data: dict) -> dict:
    body = strip_code_blocks(text)
    found = fcp.extract_all(body)
    unknowns = diff_unknowns(found, yaml_data)
    verdict = determine_verdict(unknowns)
    return {
        "verdict": verdict,
        "found": found,
        "unknowns": unknowns,
        "summary": {k: len(v) for k, v in unknowns.items()},
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("path")
    ap.add_argument("--known", default=str(DEFAULT_YAML))
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args(argv)

    md_path = Path(args.path)
    if not md_path.exists():
        print(f"ERR: {md_path} not found", file=sys.stderr)
        return 2
    yaml_path = Path(args.known)
    yaml_data = load_yaml(yaml_path)
    text = md_path.read_text(encoding="utf-8")
    result = check(text, yaml_data)

    payload = {
        "path": str(md_path),
        "yaml": str(yaml_path) if yaml_path.exists() else None,
        "verdict": result["verdict"],
        "summary": result["summary"],
        "unknowns": result["unknowns"],
        "found": result["found"],
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"fact-checker {result['verdict']}")
        for k, v in result["summary"].items():
            print(f"  {k}: {v} unknown")
    return 0 if result["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
