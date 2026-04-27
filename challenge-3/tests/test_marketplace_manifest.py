"""PRD §4 — marketplace.json source: './' + plugin entry."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
MANIFEST = ROOT / "aiwriting" / ".claude-plugin" / "marketplace.json"


def _load() -> dict:
    assert MANIFEST.exists(), f"marketplace.json missing: {MANIFEST}"
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_marketplace_required_top_keys():
    data = _load()
    for k in ("name", "owner", "plugins"):
        assert k in data, f"missing {k}"


def test_marketplace_owner():
    owner = _load()["owner"]
    assert owner["name"] == "Sanghun Lee"
    assert owner["email"] == "vitash1215@gmail.com"


def test_marketplace_plugin_entry_source():
    plugins = _load()["plugins"]
    assert len(plugins) == 1, f"exactly 1 plugin expected, got {len(plugins)}"
    entry = plugins[0]
    assert entry["name"] == "aiwriting"
    assert entry["source"] == "./", f"source must be './' got {entry['source']!r}"
    assert entry["version"] == "0.1.0"
    assert entry["category"] == "productivity"
