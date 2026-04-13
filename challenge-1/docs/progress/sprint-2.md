# Sprint 2: VLA Integration — Progress Report

> Date: 2026-03-30
> Status: **PASS** — All components validated

---

## Summary

Sprint 2 integrated the VLA model with the simulation pipeline: ActionConverter maps normalized VLA outputs to joint commands, ModelLoader provides SmolVLA/ScriptedPolicy factory, VLANode handles image preprocessing and inference, and a full camera→VLA→robot pipeline was validated with a single pick-and-place test.

## Results

### 2.1 Tests First (TDD)
- **Status**: Complete
- `tests/test_sprint2_executor.py`: 20 tests (18 fast + 2 slow/gpu)
  - ActionConverter: 7 tests (normalization, extremes, clipping, gripper, delta mode)
  - ModelLoader: 3 tests (scripted, unknown, available models)
  - VLANode: 5 tests (creation, preprocessing, prediction, no-image, timing)
  - Pipeline: 3 tests (camera→VLA→action, trajectory, robot integration)
  - SmolVLA GPU: 2 tests (load, inference — slow/gpu marked)

### 2.2 VLA Node
- **Status**: Complete
- `src/executor/vla_node.py`: Main inference entry point
  - Model loading via ModelLoader factory
  - Image preprocessing (resize to 224x224, normalize to [0,1])
  - Inference timing tracking
  - Trajectory generation (delegates to model.get_trajectory or single predict)
  - Model info reporting

### 2.3 Action Converter
- **Status**: Complete
- `src/executor/action_converter.py`: VLA output → robot commands
  - `normalized_to_joint_angles()`: [-1,1] → joint angle range with limit clipping
  - `gripper_to_width()`: [0,1] VLA gripper → physical width (0=closed, 0.04=open)
  - `convert()`: Full RobotAction → (joint_positions, gripper_width)
  - `apply_delta()`: Delta mode for incremental joint updates with scaling

### 2.4 Model Loader
- **Status**: Complete
- `src/executor/models/model_loader.py`: Factory pattern
  - `ModelLoader.load("scripted")` → ScriptedPolicy
  - `ModelLoader.load("smolvla")` → SmolVLAWrapper (MPS device)
  - `SmolVLAWrapper`: Wraps LeRobot SmolVLAPolicy with predict() interface
  - VLAModel Protocol for type safety

### 2.5 Single Pick-and-Place Test
- **Status**: Complete
- `scripts/test_single_pick.py`: End-to-end demo script
  - Initializes all components (camera, VLA, converter, robot)
  - Captures camera image → VLA inference → trajectory execution
  - Robot successfully moves from home position to pick target
  - Supports `--model smolvla`, `--live` (ZMQ), `--item`, `--shelf` flags
  - Generates structured JSONL log + before/after screenshots

### 2.6 ZMQ Bridge
- **Status**: Already complete from Sprint 1
- `src/executor/bridge_host.py` and `src/simulation/bridge_docker.py` work with VLA pipeline
- Mock mode used for all testing; ZMQ mode available for Docker integration

## Test Results

```
tests/test_sprint2_executor.py — 18 passed, 2 deselected (slow/gpu)
Total All Sprints:               59 passed, 7 deselected, 0 failed
```

## File Inventory (Sprint 2)

| File | Purpose |
|------|---------|
| `src/executor/vla_node.py` | VLA inference node (preprocessing, prediction, timing) |
| `src/executor/action_converter.py` | VLA normalized output → joint commands |
| `src/executor/models/model_loader.py` | SmolVLA/ScriptedPolicy factory + SmolVLAWrapper |
| `scripts/test_single_pick.py` | End-to-end single pick-and-place demo |
| `tests/test_sprint2_executor.py` | 20 tests (TDD) |

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| ActionConverter separate from VLANode | Single responsibility; converter reusable with any model |
| SmolVLAWrapper around LeRobot policy | Adapts LeRobot's interface to our predict(instruction, image) API |
| Delta mode in ActionConverter | Supports both absolute and incremental VLA outputs |
| ModelLoader factory pattern | Easy to add new models (Octo, OpenVLA, etc.) |

## Single Pick Test Output

```
Model: scripted | Mode: mock
Target: apple from shelf A
Trajectory steps: 5 (approach → grasp → lift → place → release)
Robot moved from home: True
Status: SUCCESS
```

## Next Steps (Sprint 3)

Sprint 3 will build the Agentic Orchestrator:
- Planner: claude -p wrapper for order parsing and plan generation
- Verifier: image-based pick success/failure verification
- Task Manager: state machine (IDLE→PLANNING→EXECUTING→VERIFYING→...)
- Picking loop: Plan→Execute→Verify integrated loop
