#!/usr/bin/env python3
"""Sprint 2: Single pick-and-place test.

End-to-end test: Camera → VLA → ActionConverter → Robot
Runs in mock mode by default. Use --live for Docker/ZMQ mode.

Usage:
    python scripts/test_single_pick.py
    python scripts/test_single_pick.py --live
    python scripts/test_single_pick.py --model smolvla
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.common.logger import StructuredLogger
from src.common.types import RobotAction
from src.executor.action_converter import ActionConverter
from src.executor.vla_node import VLANode
from src.simulation.camera_capture import CameraCapture
from src.simulation.robot_control import RobotController


def run_single_pick(
    model_type: str = "scripted",
    mode: str = "mock",
    item: str = "apple",
    shelf: str = "A",
    save_dir: str = "docs/progress",
) -> dict:
    """Run a single pick-and-place operation.

    Args:
        model_type: VLA model to use ('scripted' or 'smolvla').
        mode: 'mock' or 'zmq' for communication.
        item: Item name to pick.
        shelf: Shelf ID where the item is located.
        save_dir: Directory to save screenshots and logs.

    Returns:
        Dict with results: success, timings, actions taken.
    """
    save_path = Path(save_dir)
    save_path.mkdir(parents=True, exist_ok=True)
    logger = StructuredLogger(save_path / "single_pick_log.jsonl")

    print(f"{'='*60}")
    print(f"  Single Pick-and-Place Test")
    print(f"  Model: {model_type} | Mode: {mode}")
    print(f"  Target: {item} from shelf {shelf}")
    print(f"{'='*60}\n")

    # 1. Initialize components
    logger.info("init", "Starting components", {"model": model_type, "mode": mode})

    camera = CameraCapture(mode=mode)
    vla = VLANode(model_type=model_type)
    converter = ActionConverter()
    robot = RobotController(mode=mode)

    print(f"[1/6] Components initialized")
    print(f"       VLA ready: {vla.is_ready()}")
    print(f"       Model info: {vla.model_info}")

    # 2. Go to home position
    robot.go_home()
    logger.info("robot", "Home position", {"joints": robot._current_joints})
    print(f"[2/6] Robot at home position")

    # 3. Capture camera image
    image = camera.capture()
    if image is not None:
        camera.capture_and_save(save_path / "pick_before.png")
        print(f"[3/6] Camera image captured: {image.shape}")
    else:
        print(f"[3/6] Camera: no image (mode={mode})")

    # 4. VLA inference — generate pick trajectory
    instruction = f"pick the {item} from shelf {shelf}"
    print(f"\n[4/6] VLA Inference: '{instruction}'")

    t0 = time.time()
    trajectory = vla.get_trajectory(instruction=instruction, image=image)
    inference_time = time.time() - t0

    print(f"       Trajectory steps: {len(trajectory)}")
    print(f"       Inference time: {inference_time:.3f}s")
    logger.info("vla", "Inference complete", {
        "instruction": instruction,
        "steps": len(trajectory),
        "time": inference_time,
    })

    # 5. Execute trajectory
    print(f"\n[5/6] Executing trajectory...")
    actions_taken = []
    for i, action in enumerate(trajectory):
        joint_positions, gripper_width = converter.convert(action)

        robot.set_joint_positions(joint_positions)
        robot.set_gripper(gripper_width)

        state = robot.get_joint_state()
        actions_taken.append({
            "step": i,
            "joints": joint_positions,
            "gripper": gripper_width,
        })

        print(f"       Step {i+1}/{len(trajectory)}: "
              f"joints={[f'{j:.2f}' for j in joint_positions[:3]]}... "
              f"gripper={gripper_width:.3f}")

        logger.info("robot", f"Step {i}", {
            "joints": joint_positions,
            "gripper": gripper_width,
        })

    # 6. Final state capture
    final_image = camera.capture()
    if final_image is not None:
        camera.capture_and_save(save_path / "pick_after.png")

    # Results
    final_state = robot.get_joint_state()
    moved = any(
        abs(a - b) > 0.01
        for a, b in zip(final_state.positions, RobotController.HOME_POSITION)
    )

    result = {
        "success": moved,
        "model_type": model_type,
        "item": item,
        "shelf": shelf,
        "trajectory_steps": len(trajectory),
        "inference_time": inference_time,
        "actions_taken": len(actions_taken),
        "robot_moved": moved,
        "final_joints": final_state.positions,
    }

    logger.info("result", "Pick complete", result)

    print(f"\n[6/6] Result:")
    print(f"       Robot moved from home: {moved}")
    print(f"       Final joints: {[f'{j:.2f}' for j in final_state.positions]}")
    print(f"       Status: {'SUCCESS' if moved else 'FAILED'}")
    print(f"\n{'='*60}")

    return result


def main():
    parser = argparse.ArgumentParser(description="Single pick-and-place test")
    parser.add_argument("--model", default="scripted", choices=["scripted", "smolvla"])
    parser.add_argument("--live", action="store_true", help="Use ZMQ/Docker mode")
    parser.add_argument("--item", default="apple")
    parser.add_argument("--shelf", default="A")
    args = parser.parse_args()

    mode = "zmq" if args.live else "mock"
    result = run_single_pick(
        model_type=args.model,
        mode=mode,
        item=args.item,
        shelf=args.shelf,
    )

    sys.exit(0 if result["success"] else 1)


if __name__ == "__main__":
    main()
