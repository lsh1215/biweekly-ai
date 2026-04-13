# Architecture — Warehouse Picker VLA

## System Overview

The Warehouse Picker VLA is a hierarchical agentic system where an LLM orchestrator directs a Vision-Language-Action model to autonomously pick items from warehouse shelves.

## Data Flow

```
1. User Input
   "Order #1234: apple, bottle, book"
        │
        ▼
2. Planner.parse_order()
   Extracts: order_id="1234", items=["apple", "bottle", "book"]
   Maps items → shelf locations from configs/objects.yaml + warehouse.yaml
        │
        ▼
3. Planner.plan()
   Creates PickTask list:
     [PickTask(apple, ShelfA, z=0.5), PickTask(bottle, ShelfA, z=0.8), ...]
        │
        ▼
4. TaskManager.load_order()
   Initializes state machine: all tasks → IDLE
        │
        ▼
5. PickingLoop — for each task:
   │
   ├─► TaskManager.transition(IDLE → PLANNING)
   │   Planner.generate_instruction(task)
   │   → "pick the apple from shelf A"
   │
   ├─► TaskManager.transition(PLANNING → EXECUTING)
   │   CameraCapture.capture() → RGB image (640×480)
   │   VLANode.predict(image, instruction)
   │     ├─ preprocess: resize 224×224, normalize [0,1]
   │     └─ model.predict() → RobotAction(joint_angles, gripper)
   │   ActionConverter.convert(action) → (joint_positions, gripper_width)
   │   RobotController.set_joint_positions() + set_gripper()
   │
   ├─► TaskManager.transition(EXECUTING → VERIFYING)
   │   CameraCapture.capture() → post-action image
   │   Verifier.verify_pick(image, item_name)
   │   → VerificationResult(success, confidence, reason, suggested_action)
   │
   └─► Branch:
       ├─ SUCCESS → TaskManager.transition(VERIFYING → SUCCESS)
       │            robot.go_home(), next task
       │
       └─ FAILURE → TaskManager.transition(VERIFYING → REPLANNING)
                    Planner.replan(failed_task)
                      ├─ "drop"/"fall" → z=0.1 (floor pickup)
                      └─ "miss"/"grip" → same location (retry)
                    TaskManager.transition(REPLANNING → EXECUTING)
                      ├─ attempts < max (3) → retry loop
                      └─ attempts >= max → auto-SKIPPED

6. Report
   TaskManager.generate_report()
   → {order_id, total, completed, skipped, success_rate, items[], history[]}
```

## Component Details

### Orchestrator Layer

#### Planner (`src/orchestrator/planner.py`)
- **parse_order()**: Regex extraction of order ID + known item matching
- **plan()**: Maps items to ShelfLocations via YAML config lookup
- **replan()**: Failure-aware strategy — floor pickup for drops, same-location retry for grip misses
- **generate_instruction()**: Natural language VLA command generation

#### Verifier (`src/orchestrator/verifier.py`)
- **verify_pick()**: Post-pick image analysis — item in gripper?
- **verify_place()**: Post-place image analysis — item in collection box?
- **verify_grip()**: Mid-action grip check — gripper holding object?
- Returns `suggested_action`: "" (success), "retry" (grip miss), "replan" (drop), "skip" (unknown)

#### Task Manager (`src/orchestrator/task_manager.py`)
- **State machine**: Explicit valid transition map, ValueError on invalid transitions
- **Retry tracking**: Attempt counter incremented on EXECUTING entry
- **Auto-skip**: Attempts >= max_attempts (3) when transitioning to EXECUTING → auto-SKIPPED
- **Callbacks**: `on_transition()` for logging/monitoring

### Executor Layer

#### VLA Node (`src/executor/vla_node.py`)
- **Model loading**: Factory pattern via ModelLoader (SmolVLA on MPS, ScriptedPolicy fallback)
- **Preprocessing**: PIL resize to 224x224, float32 normalization
- **Inference**: Timed prediction, tracks total inferences

#### Action Converter (`src/executor/action_converter.py`)
- **normalized_to_joint_angles()**: [-1,1] → joint angle range with limit clipping
- **gripper_to_width()**: [0,1] → physical width (0=closed, 0.04m=open)
- **apply_delta()**: Incremental joint updates with scaling

### Simulation Layer

#### Gazebo Environment (`docker/` + `src/simulation/`)
- **Docker**: ROS2 Jazzy + Gazebo Harmonic, 6GB memory limit
- **World**: 3 shelves (A,B,C), 6 objects with physics, collection box, overhead camera
- **Robot**: 6-DOF Panda-like arm, PID position controllers, prismatic gripper
- **Bridge**: ZMQ pub/sub (port 5555/5556) for Docker ↔ macOS host

### Communication

```
┌──────────────────┐     ZMQ 5555     ┌──────────────────┐
│  Docker (Gazebo)  │ ──────────────► │  macOS Host       │
│  bridge_docker.py │   camera imgs   │  bridge_host.py   │
│                   │ ◄────────────── │  vla_node.py      │
│  robot_control    │   joint cmds    │  action_converter  │
│  camera_capture   │     ZMQ 5556    │  planner/verifier  │
└──────────────────┘                  └──────────────────┘
```

## Error Recovery Strategies

| Failure Type | Detection | Recovery Strategy |
|-------------|-----------|-------------------|
| Grip miss | Verifier: object still on shelf | Retry from same location |
| Object drop | Verifier: object on floor | Replan: pick from floor (z=0.1) |
| Object teleport | Verifier: object not found | Replan: search new location |
| Max retries exceeded | TaskManager: attempts >= 3 | Skip item, continue order |

## Configuration

Three YAML config files define the environment:

- `configs/warehouse.yaml`: Shelf positions, collection box, camera placement
- `configs/robot.yaml`: Joint limits, home position, gripper parameters
- `configs/objects.yaml`: Object names, shelf assignments, physical properties

## Testing Strategy

| Sprint | Tests | Focus |
|--------|-------|-------|
| 0 | 14 | MPS availability, SmolVLA loading, claude -p wrapper |
| 1 | 31 | Docker config, SDF validation, robot control, camera |
| 2 | 20 | Action converter, model loader, VLA node, pipeline |
| 3 | 40 | Planner, verifier, task manager, state machine |
| 4 | 19 | Grip failure, drop recovery, multi-item, integration |
| 5 | 15 | Logging, replay, reasoning trace, benchmark, adversarial |
| **Total** | **139** | |

All tests run in mock mode by default. GPU/Docker/Vision tests are marked `slow`/`gpu`/`docker`/`vision` and skipped in CI.
