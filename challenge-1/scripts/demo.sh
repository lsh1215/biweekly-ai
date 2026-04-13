#!/bin/bash
# Warehouse Picker VLA — Demo Script
# Runs a full picking scenario in mock mode to showcase the system.

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

# Activate venv
source .venv/bin/activate

echo "============================================"
echo "  Warehouse Picker VLA — System Demo"
echo "============================================"
echo ""

# 1. Single pick-and-place
echo "--- [1/4] Single Pick-and-Place ---"
python scripts/test_single_pick.py --model scripted --item apple --shelf A
echo ""

# 2. Multi-item order with error recovery
echo "--- [2/4] Multi-Item Order (with error recovery) ---"
python -c "
from src.orchestrator.picking_loop import PickingLoop
import json

loop = PickingLoop(mock_mode=True)
report = loop.process_order('Order #DEMO: apple, bottle, book, can')
print(json.dumps(report, indent=2))
"
echo ""

# 3. Adversarial demo
echo "--- [3/4] Adversarial Demo (object teleport) ---"
python -c "
from scripts.demo_adversarial import AdversarialDemo

demo = AdversarialDemo(mock_mode=True)
report = demo.run_full_demo()
print(f'Scenarios: {report[\"total\"]}')
print(f'Recovered: {report[\"recovered\"]}/{report[\"total\"]}')
print(f'Recovery rate: {report[\"recovery_rate\"]:.0%}')
"
echo ""

# 4. Benchmark comparison
echo "--- [4/4] A/B Benchmark: VLA-Only vs Agent+VLA ---"
python -c "
from scripts.benchmark import run_benchmark
import json

results = run_benchmark(num_items=6, num_trials=3)
print(f'VLA-Only:   {results[\"vla_only\"][\"avg_success_rate\"]:.0%} success rate')
print(f'Agent+VLA:  {results[\"agent_vla\"][\"avg_success_rate\"]:.0%} success rate')
print(f'Improvement: +{results[\"improvement\"]*100:.1f}%')
"
echo ""

echo "============================================"
echo "  Demo Complete!"
echo "============================================"
