"""Sprint 4: Error Recovery + Multi-Item tests.

TDD — these tests are written BEFORE implementation.
Tests: grip failure detection, drop recovery, multi-item sequential,
skip+continue, final order report.
"""

from __future__ import annotations

import pytest

from src.common.types import (
    Order,
    PickTask,
    ShelfLocation,
    TaskState,
    VerificationResult,
)
from src.orchestrator.planner import Planner
from src.orchestrator.task_manager import TaskManager
from src.orchestrator.verifier import Verifier


# ── Grip Failure Detection ──────────────────────────────────────────

class TestGripFailureDetection:
    """Verifier.verify_grip detects grip success/failure."""

    def test_grip_success(self):
        verifier = Verifier(mock_mode=True, mock_success=True)
        import numpy as np
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = verifier.verify_grip(image, "apple")
        assert result.success is True
        assert result.confidence > 0.5

    def test_grip_failure(self):
        verifier = Verifier(mock_mode=True, mock_success=False)
        import numpy as np
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = verifier.verify_grip(image, "apple")
        assert result.success is False
        assert result.suggested_action == "retry"

    def test_grip_failure_reason_contains_item(self):
        verifier = Verifier(mock_mode=True, mock_success=False)
        import numpy as np
        image = np.zeros((480, 640, 3), dtype=np.uint8)
        result = verifier.verify_grip(image, "bottle")
        assert "bottle" in result.reason.lower()


# ── Drop Recovery (Floor Pickup) ────────────────────────────────────

class TestDropRecovery:
    """Planner.replan generates floor pickup strategy for drops."""

    def test_replan_drop_sets_floor_z(self):
        planner = Planner(mock_mode=True)
        failed = PickTask(
            item_name="apple",
            location=ShelfLocation(shelf_id="A", slot=1, x=2.0, y=0.0, z=0.8),
            failure_reason="apple dropped to the floor",
        )
        new_task = planner.replan(failed)
        assert new_task.location.z < 0.2  # floor level

    def test_replan_drop_keeps_xy(self):
        planner = Planner(mock_mode=True)
        failed = PickTask(
            item_name="bottle",
            location=ShelfLocation(shelf_id="B", slot=0, x=2.0, y=1.5, z=0.5),
            failure_reason="bottle fell during grip",
        )
        new_task = planner.replan(failed)
        assert new_task.location.x == failed.location.x
        assert new_task.location.y == failed.location.y

    def test_replan_grip_failure_keeps_original_z(self):
        planner = Planner(mock_mode=True)
        failed = PickTask(
            item_name="can",
            location=ShelfLocation(shelf_id="C", slot=2, x=2.0, y=-1.5, z=1.1),
            failure_reason="grip missed the object",
        )
        new_task = planner.replan(failed)
        assert new_task.location.z == failed.location.z  # retry from same shelf

    def test_generate_instruction_floor(self):
        planner = Planner(mock_mode=True)
        task = PickTask(
            item_name="apple",
            location=ShelfLocation(shelf_id="A", slot=0, x=2.0, y=0.0, z=0.1),
        )
        instruction = planner.generate_instruction(task)
        assert "floor" in instruction.lower()

    def test_generate_instruction_shelf(self):
        planner = Planner(mock_mode=True)
        task = PickTask(
            item_name="apple",
            location=ShelfLocation(shelf_id="A", slot=0, x=2.0, y=0.0, z=0.8),
        )
        instruction = planner.generate_instruction(task)
        assert "shelf" in instruction.lower()


# ── Multi-Item Sequential Processing ────────────────────────────────

class TestMultiItemProcessing:
    """TaskManager handles multi-item orders with task queue."""

    def test_load_multi_item_order(self):
        tm = TaskManager()
        order = Order(order_id="100", items=["apple", "bottle", "book"])
        tm.load_order(order)
        assert len(tm.tasks) == 3

    def test_sequential_task_processing(self):
        tm = TaskManager()
        order = Order(order_id="101", items=["apple", "bottle"])
        tm.load_order(order)

        # Process first
        task1 = tm.get_next_task()
        assert task1 is not None
        assert task1.item_name == "apple"
        tm.transition(task1, TaskState.PLANNING)
        tm.transition(task1, TaskState.EXECUTING)
        tm.transition(task1, TaskState.VERIFYING)
        tm.transition(task1, TaskState.SUCCESS)

        # Process second
        task2 = tm.get_next_task()
        assert task2 is not None
        assert task2.item_name == "bottle"

    def test_all_success_completes_order(self):
        tm = TaskManager()
        order = Order(order_id="102", items=["apple", "bottle"])
        tm.load_order(order)

        for task in tm.tasks:
            tm.transition(task, TaskState.PLANNING)
            tm.transition(task, TaskState.EXECUTING)
            tm.transition(task, TaskState.VERIFYING)
            tm.transition(task, TaskState.SUCCESS)

        assert tm.is_complete()

    def test_mixed_success_and_skip(self):
        tm = TaskManager()
        order = Order(order_id="103", items=["apple", "bottle"])
        tm.load_order(order)

        # First: success
        t1 = tm.tasks[0]
        tm.transition(t1, TaskState.PLANNING)
        tm.transition(t1, TaskState.EXECUTING)
        tm.transition(t1, TaskState.VERIFYING)
        tm.transition(t1, TaskState.SUCCESS)

        # Second: fail 3 times → skip
        # First attempt: IDLE → PLANNING → EXECUTING → VERIFYING → REPLANNING
        t2 = tm.tasks[1]
        tm.transition(t2, TaskState.PLANNING)
        tm.transition(t2, TaskState.EXECUTING)
        tm.transition(t2, TaskState.VERIFYING)
        tm.transition(t2, TaskState.REPLANNING)
        # Retries: REPLANNING → EXECUTING → VERIFYING → REPLANNING
        for _ in range(2):
            tm.transition(t2, TaskState.EXECUTING)
            tm.transition(t2, TaskState.VERIFYING)
            tm.transition(t2, TaskState.REPLANNING)
        # 4th attempt triggers auto-skip
        tm.transition(t2, TaskState.EXECUTING)
        assert t2.state == TaskState.SKIPPED

        assert tm.is_complete()


# ── Skip + Continue Logic ───────────────────────────────────────────

class TestSkipAndContinue:
    """Max retry exceeded → skip → continue with remaining items."""

    def test_max_retry_auto_skips(self):
        tm = TaskManager()
        order = Order(order_id="200", items=["apple"])
        tm.load_order(order)
        task = tm.tasks[0]

        # First attempt
        tm.transition(task, TaskState.PLANNING)
        tm.transition(task, TaskState.EXECUTING)
        tm.transition(task, TaskState.VERIFYING)
        tm.transition(task, TaskState.REPLANNING)
        # Retries via REPLANNING → EXECUTING
        for _ in range(2):
            tm.transition(task, TaskState.EXECUTING)
            tm.transition(task, TaskState.VERIFYING)
            tm.transition(task, TaskState.REPLANNING)

        # 4th transition to EXECUTING should auto-skip
        tm.transition(task, TaskState.EXECUTING)
        assert task.state == TaskState.SKIPPED
        assert task.attempts == 3

    def test_skipped_task_not_returned_by_get_next(self):
        tm = TaskManager()
        order = Order(order_id="201", items=["apple", "bottle"])
        tm.load_order(order)

        # Skip apple: first attempt then retries
        t1 = tm.tasks[0]
        tm.transition(t1, TaskState.PLANNING)
        tm.transition(t1, TaskState.EXECUTING)
        tm.transition(t1, TaskState.VERIFYING)
        tm.transition(t1, TaskState.REPLANNING)
        for _ in range(2):
            tm.transition(t1, TaskState.EXECUTING)
            tm.transition(t1, TaskState.VERIFYING)
            tm.transition(t1, TaskState.REPLANNING)
        tm.transition(t1, TaskState.EXECUTING)  # auto-skipped
        assert t1.state == TaskState.SKIPPED

        # Next should be bottle
        next_task = tm.get_next_task()
        assert next_task is not None
        assert next_task.item_name == "bottle"


# ── Final Order Report ──────────────────────────────────────────────

class TestOrderReport:
    """TaskManager.generate_report produces complete order summary."""

    def test_report_structure(self):
        tm = TaskManager()
        order = Order(order_id="300", items=["apple", "bottle", "book"])
        tm.load_order(order)

        # apple success, bottle skip, book success
        for task in tm.tasks:
            tm.transition(task, TaskState.PLANNING)
            tm.transition(task, TaskState.EXECUTING)
            tm.transition(task, TaskState.VERIFYING)
            if task.item_name == "bottle":
                tm.transition(task, TaskState.REPLANNING)
                for _ in range(2):
                    tm.transition(task, TaskState.EXECUTING)
                    tm.transition(task, TaskState.VERIFYING)
                    tm.transition(task, TaskState.REPLANNING)
                tm.transition(task, TaskState.EXECUTING)  # auto-skip
            else:
                tm.transition(task, TaskState.SUCCESS)

        report = tm.generate_report()
        assert report["order_id"] == "300"
        assert report["total_items"] == 3
        assert report["completed"] == 2
        assert report["skipped"] == 1
        assert 0.0 < report["success_rate"] < 1.0

    def test_report_items_detail(self):
        tm = TaskManager()
        order = Order(order_id="301", items=["apple"])
        tm.load_order(order)
        task = tm.tasks[0]
        tm.transition(task, TaskState.PLANNING)
        tm.transition(task, TaskState.EXECUTING)
        tm.transition(task, TaskState.VERIFYING)
        tm.transition(task, TaskState.SUCCESS)

        report = tm.generate_report()
        assert len(report["items"]) == 1
        assert report["items"][0]["name"] == "apple"
        assert report["items"][0]["state"] == "success"
        assert report["items"][0]["attempts"] == 1

    def test_report_has_history(self):
        tm = TaskManager()
        order = Order(order_id="302", items=["apple"])
        tm.load_order(order)
        task = tm.tasks[0]
        tm.transition(task, TaskState.PLANNING)
        tm.transition(task, TaskState.EXECUTING)
        tm.transition(task, TaskState.VERIFYING)
        tm.transition(task, TaskState.SUCCESS)

        report = tm.generate_report()
        assert len(report["history"]) >= 4  # at least 4 transitions


# ── PickingLoop Integration (Mock E2E) ──────────────────────────────

class TestPickingLoopMultiItem:
    """End-to-end multi-item picking with error recovery."""

    def test_three_item_order_all_success(self):
        from src.orchestrator.picking_loop import PickingLoop

        loop = PickingLoop(mock_mode=True)
        report = loop.process_order("Order #500: apple, bottle, book")
        assert report["total_items"] == 3
        assert report["completed"] == 3
        assert report["success_rate"] == 1.0

    def test_three_item_order_with_failures(self):
        """1 success, 1 retry-then-success, 1 skip."""
        from src.orchestrator.picking_loop import PickingLoop

        # Create a verifier that fails for specific items
        call_count: dict[str, int] = {}

        class SequencedVerifier(Verifier):
            """Verifier that fails first N times for specific items."""
            def __init__(self):
                super().__init__(mock_mode=True, mock_success=True)

            def verify_pick(self, image, item_name, save_dir=None):
                call_count.setdefault(item_name, 0)
                call_count[item_name] += 1

                if item_name == "apple":
                    # Always succeed
                    return VerificationResult(
                        success=True, confidence=0.95,
                        reason="apple picked successfully",
                    )
                elif item_name == "bottle":
                    # Fail first, succeed second
                    if call_count[item_name] <= 1:
                        return VerificationResult(
                            success=False, confidence=0.8,
                            reason="grip missed the bottle",
                            suggested_action="retry",
                        )
                    return VerificationResult(
                        success=True, confidence=0.9,
                        reason="bottle picked on retry",
                    )
                else:  # book
                    # Always fail
                    return VerificationResult(
                        success=False, confidence=0.7,
                        reason="book dropped to floor",
                        suggested_action="replan",
                    )

        loop = PickingLoop(
            verifier=SequencedVerifier(),
            mock_mode=True,
        )
        report = loop.process_order("Order #501: apple, bottle, book")

        assert report["total_items"] == 3
        assert report["completed"] >= 2  # apple + bottle succeed
        assert report["skipped"] >= 1    # book skipped after max retries
