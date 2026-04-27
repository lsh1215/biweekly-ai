#!/bin/bash
# Sprint-3 D12: live dogfood, 4 format × 1 topic = 4 live writer calls.
#
# For each format, picks a fixed fixture under fixtures/inputs/<format>/
# as the dogfood input. Calls `claude -p` once, scrubs the output, then
# runs copy-killer + fact-checker on the scrubbed draft.
#
# Outputs: fixtures/dogfood/{format}.md (4 files).
# Each call costs ~$0.066 (Sonnet writer); 4 calls ~$0.26.
set -uo pipefail
cd "$(dirname "$0")/.."
[ -d ".venv" ] || { echo "ERR: .venv missing (D5)"; exit 3; }
source .venv/bin/activate

mkdir -p fixtures/dogfood
mkdir -p logs

# Bash 3.2 compatible (no associative arrays): pairs as "fmt|fixture-path".
PAIRS=(
  "blog|fixtures/inputs/blog/kafka-eos.yml"
  "cover-letter|fixtures/inputs/cover-letter/ai-startup-ml-new.yml"
  "paper|fixtures/inputs/paper/cost-aware-rag.yml"
  "letter|fixtures/inputs/letter/thanks-mentor.yml"
)

LOG="logs/dogfood.$(date -u +%Y%m%dT%H%M%SZ).log"
echo "dogfood run start: $(date -Iseconds)" | tee -a "$LOG"

ok=0
for entry in "${PAIRS[@]}"; do
  fmt="${entry%%|*}"
  fixture="${entry##*|}"
  out_md="fixtures/dogfood/${fmt}.md"
  echo "[${fmt}] fixture=${fixture}" | tee -a "$LOG"

  python3 - "$fixture" "$out_md" "$fmt" <<'PY' 2>>"$LOG"
import json, subprocess, sys
from pathlib import Path
sys.path.insert(0, "scripts")
import replay_common as rc

fixture_path = Path(sys.argv[1])
out_md = Path(sys.argv[2])
fmt = sys.argv[3]
fixture = rc.load_yaml_fixture(fixture_path)
request = rc.build_request(fixture)
system = request["system"]
user = request["messages"][0]["content"]
cmd = ["claude", "-p", user, "--output-format", "json",
       "--model", rc.WRITER_MODEL,
       "--append-system-prompt", system]
proc = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
if proc.returncode != 0:
    print(f"FAIL: claude returncode {proc.returncode}", file=sys.stderr)
    print(proc.stderr[:600], file=sys.stderr)
    sys.exit(2)
data = json.loads(proc.stdout)
text = data.get("result") or ""
if not text and isinstance(data.get("content"), list):
    text = "".join(b.get("text", "") for b in data["content"] if b.get("type") == "text")
text = rc.clean_draft_markdown(text)

import scrubber as sc
scrubbed, report = sc.scrub(text, fmt)
out_md.parent.mkdir(parents=True, exist_ok=True)
out_md.write_text(scrubbed, encoding="utf-8")
print(f"WROTE {out_md} chars={len(scrubbed)} scrubber={report.verdict} applied={report.applied}")
PY

  rc=$?
  if [ "$rc" != "0" ] || [ ! -s "$out_md" ]; then
    echo "  FAIL: ${out_md} not produced (rc=${rc})" | tee -a "$LOG"
    continue
  fi

  python3 scripts/copy_killer.py "$out_md" --threshold 0.35 --json > "fixtures/dogfood/${fmt}.copy_killer.json" || true
  python3 scripts/fact_checker.py "$out_md" --known known_facts.yml.example --json > "fixtures/dogfood/${fmt}.fact_checker.json" || true

  echo "  OK ${out_md}" | tee -a "$LOG"
  ok=$((ok + 1))
done

count=$(find fixtures/dogfood -maxdepth 1 -name '*.md' | wc -l | tr -d ' ')
echo "dogfood done: ${count}/4 outputs at $(date -Iseconds)" | tee -a "$LOG"
[ "$count" = "4" ]
