#!/usr/bin/env bash
# Sprint 4 gate: VERIFY.sh full E2E + cost under budget.
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Activate project venv if present (homebrew PEP 668 blocks global pip — Sprint 0 convention).
if [ -f "$ROOT_DIR/.venv/bin/activate" ]; then
  # shellcheck disable=SC1091
  source "$ROOT_DIR/.venv/bin/activate"
fi

echo "[checkpoint-4] running VERIFY.sh (includes pytest regression + cost check)"
bash VERIFY.sh

echo "[checkpoint-4] PASS"
