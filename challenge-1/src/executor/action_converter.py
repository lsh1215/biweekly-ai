"""Convert VLA model outputs to robot joint commands.

Maps normalized [-1,1] VLA outputs to actual joint angles within limits,
and maps gripper values to physical gripper widths.
"""

from __future__ import annotations

from src.common.types import RobotAction


class ActionConverter:
    """Converts VLA normalized outputs to robot-specific joint commands."""

    # Joint limits from robot.yaml / SDF (radians)
    JOINT_LIMITS = [
        (-2.8973, 2.8973),   # joint1
        (-1.7628, 1.7628),   # joint2
        (-2.8973, 2.8973),   # joint3
        (-3.0718, -0.0698),  # joint4
        (-2.8973, 2.8973),   # joint5
        (-0.0175, 3.7525),   # joint6
    ]

    GRIPPER_MAX_WIDTH = 0.04  # per finger, meters

    def __init__(self, joint_limits: list[tuple[float, float]] | None = None,
                 gripper_max_width: float = 0.04):
        self.joint_limits = joint_limits or list(self.JOINT_LIMITS)
        self.gripper_max_width = gripper_max_width

    def normalized_to_joint_angles(self, normalized: list[float]) -> list[float]:
        """Convert normalized [-1,1] values to joint angles within limits.

        Args:
            normalized: List of 6 values in [-1, 1].

        Returns:
            List of 6 joint angles in radians, clipped to limits.
        """
        if len(normalized) != 6:
            raise ValueError(f"Expected 6 joint values, got {len(normalized)}")

        angles = []
        for i, val in enumerate(normalized):
            # Clip to [-1, 1]
            val = max(-1.0, min(1.0, val))
            lo, hi = self.joint_limits[i]
            # Map [-1,1] → [lo, hi]
            angle = lo + (val + 1.0) / 2.0 * (hi - lo)
            angles.append(angle)

        return angles

    def gripper_to_width(self, gripper_value: float) -> float:
        """Convert VLA gripper value to physical width.

        Args:
            gripper_value: 0.0 = open, 1.0 = closed.

        Returns:
            Gripper width in meters (0.0 = closed, max_width = open).
        """
        gripper_value = max(0.0, min(1.0, gripper_value))
        return self.gripper_max_width * (1.0 - gripper_value)

    def convert(self, action: RobotAction) -> tuple[list[float], float]:
        """Convert a full VLA RobotAction to joint positions + gripper width.

        Args:
            action: RobotAction with normalized joint_angles and gripper.

        Returns:
            Tuple of (joint_positions, gripper_width).
        """
        joint_positions = self.normalized_to_joint_angles(action.joint_angles)
        gripper_width = self.gripper_to_width(action.gripper)
        return joint_positions, gripper_width

    def apply_delta(self, current: list[float], delta: list[float],
                    scale: float = 1.0) -> list[float]:
        """Apply delta actions to current joint positions.

        Args:
            current: Current joint angles (6 values).
            delta: Delta values from VLA (6 values, normalized).
            scale: Scaling factor for deltas.

        Returns:
            New joint angles, clipped to limits.
        """
        if len(current) != 6 or len(delta) != 6:
            raise ValueError("Expected 6 values for current and delta")

        result = []
        for i, (cur, d) in enumerate(zip(current, delta)):
            new_angle = cur + d * scale
            lo, hi = self.joint_limits[i]
            result.append(max(lo, min(hi, new_angle)))

        return result
