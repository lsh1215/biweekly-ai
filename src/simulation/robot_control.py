"""Robot arm control interface for Gazebo simulation.

Provides a high-level API to command the robot arm joints and gripper
via Gazebo transport topics or through the ZMQ bridge.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any

from src.common.types import RobotAction


@dataclass
class JointState:
    """Current robot joint state."""

    names: list[str]
    positions: list[float]
    timestamp: float = 0.0


class RobotController:
    """Control the simulated robot arm.

    Supports two modes:
    - zmq: Send commands through ZMQ bridge (Docker <-> Host)
    - mock: Return simulated states for testing
    """

    # Joint names matching the SDF
    JOINT_NAMES = ["joint1", "joint2", "joint3", "joint4", "joint5", "joint6"]
    GRIPPER_NAMES = ["gripper_joint_left", "gripper_joint_right"]

    # Home position (radians)
    HOME_POSITION = [0.0, -0.785, 0.0, -2.356, 0.0, 1.571]

    # Joint limits from SDF
    JOINT_LIMITS = [
        (-2.8973, 2.8973),   # joint1
        (-1.7628, 1.7628),   # joint2
        (-2.8973, 2.8973),   # joint3
        (-3.0718, -0.0698),  # joint4
        (-2.8973, 2.8973),   # joint5
        (-0.0175, 3.7525),   # joint6
    ]

    GRIPPER_MAX_WIDTH = 0.04  # per finger

    def __init__(self, mode: str = "mock", bridge: Any = None):
        self.mode = mode
        self.bridge = bridge
        self._current_joints = list(self.HOME_POSITION)
        self._current_gripper = 0.04  # open

    def go_home(self) -> bool:
        """Move robot to home position."""
        return self.set_joint_positions(self.HOME_POSITION)

    def set_joint_positions(self, positions: list[float]) -> bool:
        """Command robot joints to target positions.

        Args:
            positions: List of 6 joint angles in radians.

        Returns:
            True if command was sent successfully.
        """
        if len(positions) != 6:
            raise ValueError(f"Expected 6 joint positions, got {len(positions)}")

        # Clip to joint limits
        clipped = []
        for i, (pos, (lo, hi)) in enumerate(zip(positions, self.JOINT_LIMITS)):
            clipped.append(max(lo, min(hi, pos)))

        if self.mode == "zmq" and self.bridge:
            self.bridge.send_joint_command(clipped)

        self._current_joints = clipped
        return True

    def set_gripper(self, width: float) -> bool:
        """Set gripper opening width.

        Args:
            width: Opening width per finger (0.0 = closed, 0.04 = fully open).

        Returns:
            True if command was sent.
        """
        width = max(0.0, min(self.GRIPPER_MAX_WIDTH, width))

        if self.mode == "zmq" and self.bridge:
            self.bridge.send_gripper_command(width)

        self._current_gripper = width
        return True

    def open_gripper(self) -> bool:
        """Fully open the gripper."""
        return self.set_gripper(self.GRIPPER_MAX_WIDTH)

    def close_gripper(self) -> bool:
        """Fully close the gripper."""
        return self.set_gripper(0.0)

    def execute_action(self, action: RobotAction) -> bool:
        """Execute a VLA-generated robot action.

        Args:
            action: RobotAction with joint_angles and gripper state.

        Returns:
            True if all commands sent.
        """
        success = self.set_joint_positions(action.joint_angles)

        # gripper: 0.0 = open, 1.0 = closed in VLA convention
        gripper_width = self.GRIPPER_MAX_WIDTH * (1.0 - action.gripper)
        success = success and self.set_gripper(gripper_width)

        return success

    def get_joint_state(self) -> JointState:
        """Get current joint state."""
        if self.mode == "zmq" and self.bridge:
            state = self.bridge.receive_joint_state(timeout=1000)
            if state:
                return JointState(
                    names=state.get("names", self.JOINT_NAMES),
                    positions=state.get("positions", self._current_joints),
                    timestamp=state.get("timestamp", time.time()),
                )

        return JointState(
            names=self.JOINT_NAMES,
            positions=self._current_joints,
            timestamp=time.time(),
        )
