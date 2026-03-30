"""Picking loop — integrates Planner, VLA Executor, Verifier, and Task Manager.

Orchestrates the full Plan → Execute → Verify loop for each item in an order.
"""

from __future__ import annotations

from typing import Any

from src.common.logger import StructuredLogger
from src.common.types import Order, TaskState, VerificationResult
from src.executor.action_converter import ActionConverter
from src.executor.vla_node import VLANode
from src.orchestrator.planner import Planner
from src.orchestrator.task_manager import TaskManager
from src.orchestrator.verifier import Verifier
from src.simulation.camera_capture import CameraCapture
from src.simulation.robot_control import RobotController


class PickingLoop:
    """End-to-end picking loop: Plan → Execute → Verify."""

    def __init__(
        self,
        planner: Planner | None = None,
        verifier: Verifier | None = None,
        task_manager: TaskManager | None = None,
        vla: VLANode | None = None,
        camera: CameraCapture | None = None,
        robot: RobotController | None = None,
        converter: ActionConverter | None = None,
        logger: StructuredLogger | None = None,
        mock_mode: bool = True,
    ):
        self.planner = planner or Planner(mock_mode=mock_mode)
        self.verifier = verifier or Verifier(mock_mode=mock_mode)
        self.task_manager = task_manager or TaskManager()
        self.vla = vla or VLANode(model_type="scripted")
        self.camera = camera or CameraCapture(mode="mock")
        self.robot = robot or RobotController(mode="mock")
        self.converter = converter or ActionConverter()
        self.logger = logger or StructuredLogger()

    def process_order(self, order_text: str) -> dict[str, Any]:
        """Process a full order from natural language to completion.

        Args:
            order_text: Natural language order string.

        Returns:
            Order completion report.
        """
        self.logger.info("loop", "Processing order", {"text": order_text})

        # 1. Parse order
        order = self.planner.parse_order(order_text)
        self.logger.info("loop", "Order parsed", {
            "id": order.order_id, "items": order.items,
        })

        # 2. Generate plan
        tasks = self.planner.plan(order)
        self.task_manager.order = order
        self.task_manager.tasks = tasks
        self.logger.info("loop", "Plan generated", {"tasks": len(tasks)})

        # 3. Execute picking loop
        while not self.task_manager.is_complete():
            task = self.task_manager.get_next_task()
            if task is None:
                break

            self._pick_item(task)

        # 4. Generate report
        report = self.task_manager.generate_report()
        self.logger.info("loop", "Order complete", report)

        return report

    def _pick_item(self, task: Any) -> None:
        """Execute a single pick task through the state machine."""
        item = task.item_name
        self.logger.info("loop", f"Picking {item}", {"attempt": task.attempts})

        if task.state == TaskState.REPLANNING:
            # Retry: REPLANNING → EXECUTING (skip PLANNING)
            instruction = self.planner.generate_instruction(task)
            self.task_manager.transition(task, TaskState.EXECUTING)
        else:
            # Fresh: IDLE → PLANNING → EXECUTING
            self.task_manager.transition(task, TaskState.PLANNING)
            instruction = self.planner.generate_instruction(task)
            self.task_manager.transition(task, TaskState.EXECUTING)

        # Check if auto-skipped due to max retries
        if task.state == TaskState.SKIPPED:
            self.logger.info("loop", f"Skipped {item}", {"reason": "max_retries"})
            return

        # Capture image
        image = self.camera.capture()

        # VLA inference
        action = self.vla.predict(image, instruction)
        self.logger.info("loop", "VLA inference", {
            "item": item,
            "instruction": instruction,
            "inference_time": self.vla.last_inference_time,
        })

        # Execute action on robot
        joint_positions, gripper_width = self.converter.convert(action)
        self.robot.set_joint_positions(joint_positions)
        self.robot.set_gripper(gripper_width)

        # EXECUTING → VERIFYING
        self.task_manager.transition(task, TaskState.VERIFYING)

        # Capture post-action image
        post_image = self.camera.capture()
        result = self.verifier.verify_pick(post_image, item)

        self.logger.info("loop", "Verification", {
            "item": item,
            "success": result.success,
            "confidence": result.confidence,
            "reason": result.reason,
        })

        if result.success:
            # VERIFYING → SUCCESS
            self.task_manager.transition(task, TaskState.SUCCESS)
            self.robot.go_home()
            self.logger.info("loop", f"Success: {item}")
        else:
            # VERIFYING → REPLANNING
            self.task_manager.transition(task, TaskState.REPLANNING)
            task.failure_reason = result.reason

            # Replan and create new task data
            new_task = self.planner.replan(task)
            task.location = new_task.location

            self.robot.go_home()
            self.logger.info("loop", f"Replanning: {item}", {
                "reason": result.reason,
                "new_location_z": new_task.location.z,
            })
