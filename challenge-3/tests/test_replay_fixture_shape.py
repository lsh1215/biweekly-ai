"""D7 replay JSON shape — 7 required keys per fixture, 16 total fixtures (writer stage)."""
import glob
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
REPLAY_DIR = ROOT / "replay" / "fixtures"

REQUIRED_KEYS = {
    "model",
    "captured_at",
    "stage",
    "request",
    "response",
    "dispatch_key",
    "format",
}

VALID_FORMATS = {"blog", "cover-letter", "paper", "letter"}
VALID_STAGES = {"writer", "structure-critic"}


def test_replay_dir_exists():
    assert REPLAY_DIR.is_dir(), f"replay/fixtures/ missing at {REPLAY_DIR}"


def test_writer_fixtures_count_is_16():
    files = sorted(REPLAY_DIR.glob("*/*-writer.json"))
    assert len(files) == 16, f"expected 16 writer fixtures, got {len(files)}: {files}"


def test_each_writer_fixture_has_required_keys():
    files = sorted(REPLAY_DIR.glob("*/*-writer.json"))
    assert files, "no writer fixtures found"
    for f in files:
        data = json.loads(f.read_text())
        missing = REQUIRED_KEYS - set(data.keys())
        assert not missing, f"{f.name} missing keys: {missing}"
        assert data["format"] in VALID_FORMATS, f"{f.name} bad format: {data['format']}"
        assert data["stage"] in VALID_STAGES, f"{f.name} bad stage: {data['stage']}"
        # request must have system/messages/tools keys
        for k in ("system", "messages", "tools"):
            assert k in data["request"], f"{f.name} request missing {k}"
        # response must have stop_reason/content
        for k in ("stop_reason", "content"):
            assert k in data["response"], f"{f.name} response missing {k}"


def test_each_writer_fixture_has_4_per_format():
    files = sorted(REPLAY_DIR.glob("*/*-writer.json"))
    by_format = {}
    for f in files:
        data = json.loads(f.read_text())
        by_format.setdefault(data["format"], []).append(f.name)
    for fmt in VALID_FORMATS:
        assert len(by_format.get(fmt, [])) == 4, (
            f"format {fmt}: expected 4, got {len(by_format.get(fmt, []))}: {by_format.get(fmt)}"
        )
