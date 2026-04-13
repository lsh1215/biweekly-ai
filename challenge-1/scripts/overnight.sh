#!/bin/bash
# Warehouse Picker VLA — Overnight Autonomous Execution
# 7-8시간 동안 Sprint 0~5를 자율 실행
# 사용법: nohup bash scripts/overnight.sh > overnight.log 2>&1 &

cd /Users/leesanghun/My_Project/VLA
LOG_DIR="docs/progress"
mkdir -p "$LOG_DIR"

echo "=============================================="
echo "  Warehouse Picker VLA — Overnight Build"
echo "  Started: $(date)"
echo "=============================================="

# ─── SESSION 1: Sprint 0 + Sprint 1 (~2.5h) ───
echo ""
echo "=== SESSION 1: Sprint 0 + Sprint 1 ($(date)) ==="
echo ""

claude -p --dangerously-skip-permissions "$(cat <<'PROMPT'
You are building the Warehouse Picker VLA project autonomously overnight.

READ THESE FILES FIRST:
1. docs/EXECUTION_PLAN.md — the full sprint plan
2. docs/PRD.md — product requirements
3. docs/TECH_STACK.md — tech stack details

YOUR TASK: Execute Sprint 0 (Risk Validation) and Sprint 1 (Simulation Environment) from the execution plan.

RULES:
- Follow TDD: write test files FIRST, then implement code to pass them
- After each sprint, write a progress report to docs/progress/sprint-N.md with: what was done, issues found, how resolved, test results
- Run pytest after each sprint to verify all tests pass
- If something fails, try the fallback plan documented in the execution plan
- Commit progress with git after each sprint
- Be thorough — the user is sleeping and will check results in the morning

IMPORTANT CONSTRAINTS:
- Do NOT read any .env files
- Use Docker for Gazebo+ROS2, local macOS for SmolVLA (MPS)
- Python venv at .venv/

START WITH Sprint 0, then Sprint 1. Stop after Sprint 1 is complete.
PROMPT
)" --max-turns 100 --verbose 2>&1 | tee -a overnight_session1.log

echo ""
echo "Session 1 completed at $(date)"
echo "Cooling down 15 minutes for rate limit reset..."
sleep 900

# ─── SESSION 2: Sprint 2 + Sprint 3 (~3h) ───
echo ""
echo "=== SESSION 2: Sprint 2 + Sprint 3 ($(date)) ==="
echo ""

claude -p --dangerously-skip-permissions "$(cat <<'PROMPT'
You are continuing the Warehouse Picker VLA project overnight build.

READ THESE FILES FIRST:
1. docs/EXECUTION_PLAN.md — the full sprint plan
2. docs/progress/sprint-0.md — what Sprint 0 accomplished (model choice, vision validation results)
3. docs/progress/sprint-1.md — what Sprint 1 accomplished (Docker, Gazebo, robot arm status)
4. docs/PRD.md — product requirements

YOUR TASK: Execute Sprint 2 (VLA Integration) and Sprint 3 (Agentic Orchestrator) from the execution plan.

RULES:
- Follow TDD: write test files FIRST, then implement
- Use the model chosen in Sprint 0 (check sprint-0.md for SmolVLA/Octo/Scripted decision)
- Use the Docker setup from Sprint 1 (check sprint-1.md for any issues/workarounds)
- Write progress reports to docs/progress/sprint-2.md and sprint-3.md
- Run pytest after each sprint
- If something fails, try the fallback plan in the execution plan
- Commit progress with git after each sprint

IMPORTANT CONSTRAINTS:
- Do NOT read any .env files
- SmolVLA runs on local macOS (MPS), Gazebo+ROS2 in Docker
- ZMQ bridge on ports 5555/5556 (or file-based fallback)
- Python venv at .venv/

START WITH Sprint 2, then Sprint 3. Stop after Sprint 3 is complete.
PROMPT
)" --max-turns 100 --verbose 2>&1 | tee -a overnight_session2.log

echo ""
echo "Session 2 completed at $(date)"
echo "Cooling down 15 minutes for rate limit reset..."
sleep 900

# ─── SESSION 3: Sprint 4 + Sprint 5 (~2h) ───
echo ""
echo "=== SESSION 3: Sprint 4 + Sprint 5 ($(date)) ==="
echo ""

claude -p --dangerously-skip-permissions "$(cat <<'PROMPT'
You are finishing the Warehouse Picker VLA project overnight build.

READ THESE FILES FIRST:
1. docs/EXECUTION_PLAN.md — the full sprint plan
2. docs/progress/sprint-0.md through sprint-3.md — all previous progress
3. docs/PRD.md — product requirements

YOUR TASK: Execute Sprint 4 (Error Recovery + Multi-Item) and Sprint 5 (Expansions + Demo + Polish) from the execution plan.

Sprint 5 includes CEO-approved expansions:
- Structured JSON logging + replay system
- LLM reasoning trace UI (rich library terminal output)
- A/B comparison visualization (VLA-only vs Agent+VLA, matplotlib chart)
- Interactive adversarial demo (object teleport during picking)
- Benchmark runs
- README.md with architecture diagram
- docs/ARCHITECTURE.md

RULES:
- Follow TDD: write test files FIRST, then implement
- Build on all previous sprint code
- Write progress reports to docs/progress/sprint-4.md and sprint-5.md
- Run full test suite: pytest tests/ -v
- Run demo script to verify end-to-end
- Commit progress with git after each sprint
- Final commit should have all tests passing and README complete

IMPORTANT CONSTRAINTS:
- Do NOT read any .env files
- Python venv at .venv/

START WITH Sprint 4, then Sprint 5. This is the final session — make it complete.
PROMPT
)" --max-turns 100 --verbose 2>&1 | tee -a overnight_session3.log

# ─── DONE ───
echo ""
echo "=============================================="
echo "  ALL SESSIONS COMPLETE"
echo "  Finished: $(date)"
echo "=============================================="
echo ""
echo "Check results:"
echo "  - Progress reports: docs/progress/sprint-*.md"
echo "  - Test results: pytest tests/ -v"
echo "  - Session logs: overnight_session*.log"
echo "  - README: README.md"
