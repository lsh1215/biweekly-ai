"""dispatch_key = sha256(utf8(request.messages[*].content text concat with \n)) — deterministic."""
import glob
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLAY_DIR = ROOT / "replay" / "fixtures"


def _compute_dispatch_key(request: dict) -> str:
    parts = []
    for msg in request.get("messages", []):
        content = msg.get("content")
        if isinstance(content, str):
            parts.append(content)
        elif isinstance(content, list):
            for block in content:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
                elif isinstance(block, str):
                    parts.append(block)
    joined = "\n".join(parts)
    return hashlib.sha256(joined.encode("utf-8")).hexdigest()


def test_dispatch_key_matches_request_messages():
    files = sorted(REPLAY_DIR.glob("*/*-writer.json"))
    assert files, "no writer fixtures"
    for f in files:
        data = json.loads(f.read_text())
        expected = _compute_dispatch_key(data["request"])
        assert data["dispatch_key"] == expected, (
            f"{f.name}: dispatch_key {data['dispatch_key'][:12]} != computed {expected[:12]}"
        )


def test_dispatch_key_is_sha256_hex_64chars():
    files = sorted(REPLAY_DIR.glob("*/*-writer.json"))
    for f in files:
        data = json.loads(f.read_text())
        key = data["dispatch_key"]
        assert len(key) == 64, f"{f.name}: dispatch_key len {len(key)}"
        int(key, 16)  # raises if not hex


def test_dispatch_keys_are_unique_across_fixtures():
    files = sorted(REPLAY_DIR.glob("*/*-writer.json"))
    keys = [json.loads(f.read_text())["dispatch_key"] for f in files]
    assert len(keys) == len(set(keys)), "dispatch_keys collide across fixtures"
