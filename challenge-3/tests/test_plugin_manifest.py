"""PRD §4 — plugin.json metadata 4 fields exact."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "aiwriting" / ".claude-plugin" / "plugin.json"


def _load() -> dict:
    assert MANIFEST.exists(), f"plugin.json missing: {MANIFEST}"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_plugin_manifest_exact_4_fields():
    data = _load()
    assert set(data.keys()) == {"name", "version", "description", "author"}, (
        f"keys must be exactly the 4 metadata fields, got {sorted(data.keys())}"
    )


def test_plugin_name():
    assert _load()["name"] == "aiwriting"


def test_plugin_version_semver():
    v = _load()["version"]
    parts = v.split(".")
    assert len(parts) == 3, f"semver expected, got {v}"
    assert all(p.isdigit() or p[0].isdigit() for p in parts), v


def test_plugin_author_block():
    author = _load()["author"]
    assert author["name"] == "Sanghun Lee"
    assert author["email"] == "vitash1215@gmail.com"


def test_plugin_description_mentions_korean_writing():
    desc = _load()["description"]
    assert "Korean" in desc or "writing" in desc.lower(), desc
