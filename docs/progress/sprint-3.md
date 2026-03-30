# Sprint 3: Agentic Orchestrator — Progress Report

> Date: 2026-03-30
> Status: **PASS** — All components validated

---

## Summary

Sprint 3 built the full agentic orchestrator: Planner (order parsing, plan generation, replanning), Verifier (vision-based pick/place/grip verification), Task Manager (state machine with valid transitions, retry tracking, event callbacks), prompt templates for claude -p, and the integrated picking loop (Plan→Execute→Verify). All 40 Sprint 3 tests pass; 99 total across all sprints.

## Results

### 3.1 Tests First (TDD)
- **Status**: Complete
- `tests/test_sprint3_planner.py`: 12 tests (parsing: 4, planning: 4, replanning: 2, claude: 2)
- `tests/test_sprint3_verifier.py`: 9 tests (pick: 3, place: 2, grip: 2, claude: 2)
- `tests/test_sprint3_task_manager.py`: 19 tests (transitions: 7, invalid: 3, retry: 3, completion: 5, callbacks: 1)

### 3.2 Common Types
- **Status**: Already complete from Sprint 0
- `TaskState` enum, `PickTask`, `VerificationResult`, `Order`, `ShelfLocation` dataclasses

### 3.3 Planner
- **Status**: Complete
- `src/orchestrator/planner.py`:
  - `parse_order()`: Extracts order ID and item names from natural language
  - `plan()`: Creates PickTasks with shelf locations from config (objects.yaml + warehouse.yaml)
  - `replan()`: Generates new strategy for failed tasks (floor pickup for drops, retry for grip failures)
  - `generate_instruction()`: Creates VLA-ready natural language commands
  - Item→shelf mapping built from YAML configs at init time
  - Mock mode for testing without Claude

### 3.4 Verifier
- **Status**: Complete
- `src/orchestrator/verifier.py`:
  - `verify_pick()`: Judges if item was picked from shelf
  - `verify_place()`: Judges if item was placed in collection box
  - `verify_grip()`: Judges if gripper is holding the object
  - Returns structured `VerificationResult` with confidence and suggested_action
  - Image saving for Claude vision analysis
  - Mock mode with configurable success/failure

### 3.5 Task Manager State Machine
- **Status**: Complete
- `src/orchestrator/task_manager.py`:
  - Full state machine: IDLE → PLANNING → EXECUTING → VERIFYING → SUCCESS/REPLANNING → SKIPPED
  - Valid transition map — invalid transitions raise ValueError
  - Attempt tracking: increments on EXECUTING, auto-skips at max_attempts (3)
  - Event callbacks: `on_transition()` with (task, old_state, new_state)
  - Order loading, next task selection, completion check
  - `generate_report()`: order summary with success rate, per-item details, history

### 3.6 Picking Loop
- **Status**: Complete
- `src/orchestrator/picking_loop.py`:
  - `process_order()`: Full end-to-end order processing
  - Integrates: Planner → VLANode → ActionConverter → RobotController → Verifier
  - State machine transitions via TaskManager
  - Structured logging at every step
  - Replan loop: failure → replan → retry (up to max_attempts)

### 3.7 Prompt Templates
- **Status**: Complete (5 templates)
- `prompts/planner_parse.txt`: Order parsing
- `prompts/planner_plan.txt`: Pick plan generation
- `prompts/planner_replan.txt`: Failure recovery planning
- `prompts/verifier_pick.txt`: Pick verification
- `prompts/verifier_place.txt`: Place verification

## Test Results

```
tests/test_sprint3_planner.py      — 12 passed
tests/test_sprint3_verifier.py     —  9 passed
tests/test_sprint3_task_manager.py — 19 passed
Sprint 3 Total:                      40 passed, 0 failed

All Sprints (0-3):                   99 passed, 7 deselected (slow/gpu/docker/vision), 0 failed
```

## File Inventory (Sprint 3)

| File | Purpose |
|------|---------|
| `src/orchestrator/planner.py` | Order parsing, plan generation, replanning |
| `src/orchestrator/verifier.py` | Vision-based pick/place/grip verification |
| `src/orchestrator/task_manager.py` | State machine, retry tracking, completion |
| `src/orchestrator/picking_loop.py` | Integrated Plan→Execute→Verify loop |
| `src/orchestrator/prompts/planner_parse.txt` | Order parsing prompt |
| `src/orchestrator/prompts/planner_plan.txt` | Plan generation prompt |
| `src/orchestrator/prompts/planner_replan.txt` | Replanning prompt |
| `src/orchestrator/prompts/verifier_pick.txt` | Pick verification prompt |
| `src/orchestrator/prompts/verifier_place.txt` | Place verification prompt |
| `tests/test_sprint3_planner.py` | 12 planner tests |
| `tests/test_sprint3_verifier.py` | 9 verifier tests |
| `tests/test_sprint3_task_manager.py` | 19 task manager tests |

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| Planner reads item locations from config YAML | Single source of truth; no hardcoded mappings |
| Verifier returns suggested_action (retry/replan/skip) | Enables autonomous recovery without external logic |
| Task Manager uses explicit valid transition map | Prevents illegal state jumps; easy to extend |
| Auto-skip on max_attempts in transition() | Guarantees progress even on persistent failures |
| PickingLoop accepts all components via DI | Fully testable with mock components |

## Architecture Validated

```
User Input → Planner (parse + plan)
                ↓
           TaskManager (IDLE → PLANNING)
                ↓
           VLANode (inference) → ActionConverter → RobotController
                ↓
           TaskManager (EXECUTING → VERIFYING)
                ↓
           Verifier (camera → judgment)
                ↓
           SUCCESS ─or─ REPLANNING → retry loop
```

## Next Steps (Sprint 4)

Sprint 4 will add error recovery and multi-item processing:
- Grip failure detection via Verifier.verify_grip()
- Drop recovery via Planner.replan() with floor pickup
- Multi-item sequential processing with task queue
- Skip + continue logic with final order report
