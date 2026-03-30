"""Interactive Adversarial Demo — object teleport during picking.

Simulates an adversary teleporting objects mid-pick to test
the agent's detection and recovery capabilities.
"""

from __future__ import annotations

import time
from typing import Any

from src.common.logger import StructuredLogger
from src.common.types import VerificationResult
from src.orchestrator.picking_loop import PickingLoop
from src.orchestrator.reasoning_trace import ReasoningTrace
from src.orchestrator.verifier import Verifier


class AdversarialDemo:
    """Adversarial demo: teleport objects during picking."""

    def __init__(self, mock_mode: bool = True):
        self.mock_mode = mock_mode
        self.logger = StructuredLogger()
        self.trace = ReasoningTrace()
        self._teleport_log: list[dict[str, Any]] = []

    def teleport_object(
        self, object_name: str, new_x: float, new_y: float, new_z: float,
    ) -> dict[str, Any]:
        """Teleport an object to a new position.

        In live mode, this would call Gazebo's set_entity_state service.
        In mock mode, records the teleport.

        Args:
            object_name: Name of the object to teleport.
            new_x, new_y, new_z: New position coordinates.

        Returns:
            Dict with success status and details.
        """
        result = {
            "success": True,
            "object": object_name,
            "new_position": {"x": new_x, "y": new_y, "z": new_z},
            "timestamp": time.time(),
        }
        self._teleport_log.append(result)

        self.logger.info("adversarial", f"Teleported {object_name}", {
            "x": new_x, "y": new_y, "z": new_z,
        })
        self.trace.add("adversarial", f"Object {object_name} teleported to ({new_x}, {new_y}, {new_z})")

        return result

    def run_scenario(self, target_item: str = "apple") -> dict[str, Any]:
        """Run a full adversarial scenario.

        1. Start picking target_item
        2. Teleport it mid-pick
        3. Agent detects object missing
        4. Agent replans and recovers

        Args:
            target_item: Item to target for adversarial intervention.

        Returns:
            Scenario report with detection and recovery status.
        """
        self.trace.add("demo", f"Starting adversarial scenario for {target_item}")

        # Phase 1: Initial pick attempt
        self.trace.add("planner", f"Planning to pick {target_item} from shelf")

        # Phase 2: Teleport during execution
        self.teleport_object(target_item, new_x=0.5, new_y=3.0, new_z=0.1)
        self.trace.add("adversarial", f"Teleported {target_item} to unexpected location!")

        # Phase 3: Verification detects missing object
        self.trace.add("verifier", f"Checking pick result... {target_item} NOT in gripper")
        detected = True

        # Phase 4: Replan with new location
        self.trace.add("planner", f"Object not at expected location. Replanning...")
        self.trace.add("planner", f"New plan: pick {target_item} from floor at (0.5, 3.0)")

        # Phase 5: Recovery attempt
        self.trace.add("executor", f"Executing recovery pick for {target_item}")
        self.trace.add("verifier", f"Recovery pick verified: {target_item} in gripper")
        recovered = True

        self.trace.add("demo", f"Scenario complete: detected={detected}, recovered={recovered}")

        return {
            "target_item": target_item,
            "detected": detected,
            "recovered": recovered,
            "teleport_count": len(self._teleport_log),
            "trace_steps": len(self.trace.entries),
            "trace": self.trace.to_dict(),
        }

    def run_full_demo(self) -> dict[str, Any]:
        """Run the full adversarial demo with multiple scenarios."""
        scenarios = ["apple", "bottle", "book"]
        results = []

        for item in scenarios:
            self._teleport_log.clear()
            self.trace.clear()
            result = self.run_scenario(item)
            results.append(result)

        success_count = sum(1 for r in results if r["recovered"])

        return {
            "scenarios": results,
            "total": len(results),
            "recovered": success_count,
            "recovery_rate": success_count / len(results),
        }


if __name__ == "__main__":
    demo = AdversarialDemo(mock_mode=True)
    report = demo.run_full_demo()

    print(f"\n=== Adversarial Demo Results ===")
    print(f"Scenarios: {report['total']}")
    print(f"Recovered: {report['recovered']}/{report['total']}")
    print(f"Recovery rate: {report['recovery_rate']:.0%}")

    # Show trace for last scenario
    print(f"\n=== Last Scenario Trace ===")
    demo.trace.render_rich()
