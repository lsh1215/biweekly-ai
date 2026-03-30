"""Scripted fallback policy for when VLA model is unavailable."""

from __future__ import annotations

import math
from src.common.types import RobotAction


class ScriptedPolicy:
    """Hardcoded trajectory policy as VLA fallback.

    Generates predefined joint trajectories for basic pick-and-place operations.
    Used when SmolVLA or other VLA models fail to load.
    """

    # Predefined positions (6-DOF joint angles in radians)
    HOME = [0.0, -0.785, 0.0, -2.356, 0.0, 1.571]
    SHELF_A = [0.5, -0.3, 0.2, -1.8, 0.3, 1.2]
    SHELF_B = [0.5, 0.3, 0.2, -1.8, 0.3, 1.2]
    SHELF_C = [0.5, -0.9, 0.2, -1.8, 0.3, 1.2]
    COLLECTION_BOX = [-0.3, -0.5, 0.1, -2.0, 0.0, 1.4]

    def predict(self, instruction: str, image: object = None) -> RobotAction:
        """Generate a robot action from a text instruction.

        Args:
            instruction: Natural language command (e.g., "pick apple from shelf A")
            image: Optional camera image (ignored in scripted mode)

        Returns:
            RobotAction with joint angles and gripper state.
        """
        instruction_lower = instruction.lower()

        if "place" in instruction_lower or "collection" in instruction_lower:
            return RobotAction(
                joint_angles=list(self.COLLECTION_BOX),
                gripper=0.0,  # open to release
            )

        # Determine target shelf
        if "shelf a" in instruction_lower or "shelf_a" in instruction_lower:
            target = self.SHELF_A
        elif "shelf b" in instruction_lower or "shelf_b" in instruction_lower:
            target = self.SHELF_B
        elif "shelf c" in instruction_lower or "shelf_c" in instruction_lower:
            target = self.SHELF_C
        else:
            # Default: go to shelf A
            target = self.SHELF_A

        return RobotAction(
            joint_angles=list(target),
            gripper=1.0,  # close to grasp
        )

    def get_trajectory(self, instruction: str) -> list[RobotAction]:
        """Generate a full pick-and-place trajectory.

        Returns a sequence of actions: approach -> grasp -> lift -> place -> release.
        """
        pick_action = self.predict(instruction)
        approach = RobotAction(
            joint_angles=[a * 0.8 for a in pick_action.joint_angles],
            gripper=0.0,
        )
        grasp = pick_action
        lift = RobotAction(
            joint_angles=[a + (0.2 if i == 1 else 0.0) for i, a in enumerate(pick_action.joint_angles)],
            gripper=1.0,
        )
        place = RobotAction(
            joint_angles=list(self.COLLECTION_BOX),
            gripper=1.0,
        )
        release = RobotAction(
            joint_angles=list(self.COLLECTION_BOX),
            gripper=0.0,
        )

        return [approach, grasp, lift, place, release]
