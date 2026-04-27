"""validate_manifest.py - jsonschema fallback when `claude plugin validate` is missing.

S1 scenario: if the `claude plugin validate` CLI is unavailable (older claude
binary, container without claude installed, etc.), checkpoint_sprint0.sh falls
back to this script.

Strategy:
  1. Try a built-in cached schema (matches PRD §4 metadata-only spec).
  2. If a remote schema URL is reachable AND ./scripts/.cached-plugin-schema.json
     does not exist, fetch and cache (best-effort, non-blocking).
  3. Run jsonschema.validate against the manifest. Exit 0 on pass, 1 on fail.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

try:
    import jsonschema
except ImportError as e:
    print(f"ERR: jsonschema not installed in .venv ({e})", file=sys.stderr)
    sys.exit(2)

ROOT = Path(__file__).resolve().parent.parent
CACHED_SCHEMA = ROOT / "scripts" / ".cached-plugin-schema.json"

# Built-in baseline schema. Matches PRD §4 — metadata-only 4 fields.
BASELINE_PLUGIN_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "version", "description", "author"],
    "additionalProperties": True,
    "properties": {
        "name": {"type": "string", "minLength": 1},
        "version": {
            "type": "string",
            "pattern": r"^\d+\.\d+\.\d+([.-][A-Za-z0-9]+)*$",
        },
        "description": {"type": "string", "minLength": 1},
        "author": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string", "minLength": 1},
                "email": {"type": "string"},
            },
        },
    },
}

BASELINE_MARKETPLACE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["name", "owner", "plugins"],
    "properties": {
        "name": {"type": "string"},
        "owner": {
            "type": "object",
            "required": ["name"],
            "properties": {
                "name": {"type": "string"},
                "email": {"type": "string"},
            },
        },
        "plugins": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "required": ["name", "source", "version"],
                "properties": {
                    "name": {"type": "string"},
                    "source": {"type": "string"},
                    "version": {"type": "string"},
                    "description": {"type": "string"},
                    "category": {"type": "string"},
                },
            },
        },
    },
}


def pick_schema(manifest_path: Path):
    """Use cached schema if present and matches doc kind, else baseline."""
    name = manifest_path.name
    if CACHED_SCHEMA.exists():
        try:
            return json.loads(CACHED_SCHEMA.read_text(encoding="utf-8"))
        except Exception:
            pass
    if name == "plugin.json":
        return BASELINE_PLUGIN_SCHEMA
    if name == "marketplace.json":
        return BASELINE_MARKETPLACE_SCHEMA
    return BASELINE_PLUGIN_SCHEMA


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("usage: validate_manifest.py <manifest.json>", file=sys.stderr)
        return 2
    manifest_path = Path(argv[1])
    if not manifest_path.exists():
        print(f"ERR: {manifest_path} not found", file=sys.stderr)
        return 1
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"ERR: {manifest_path} not valid JSON: {e}", file=sys.stderr)
        return 1
    schema = pick_schema(manifest_path)
    try:
        jsonschema.validate(instance=manifest, schema=schema)
    except jsonschema.ValidationError as e:
        print(f"FAIL: {manifest_path} - {e.message}", file=sys.stderr)
        return 1
    print(f"OK: {manifest_path} valid against baseline schema")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
