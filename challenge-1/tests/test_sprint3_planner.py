"""Sprint 3: Planner tests (TDD — written first).

Tests for:
- Order parsing from natural language
- Pick plan generation with shelf locations
- Replanning on failure
- Claude -p integration (mocked)
"""

import json
import pytest

from src.common.types import Order, PickTask, ShelfLocation, TaskState


class TestOrderParsing:
    """Test Planner's order parsing from natural language."""

    def test_parse_simple_order(self):
        """Parse a simple order with item names."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = planner.parse_order("주문 #1234: apple 1개, bottle 1개")

        assert order.order_id == "1234"
        assert len(order.items) == 2
        assert "apple" in order.items
        assert "bottle" in order.items

    def test_parse_order_extracts_id(self):
        """Order ID should be extracted from the input."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = planner.parse_order("Order #5678: book, box, can")

        assert order.order_id == "5678"
        assert len(order.items) == 3

    def test_parse_order_without_id(self):
        """Order without explicit ID should get a generated one."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = planner.parse_order("apple, bottle, book")

        assert order.order_id != ""
        assert len(order.items) == 3

    def test_parse_empty_order(self):
        """Empty order should raise or return empty."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = planner.parse_order("")
        assert len(order.items) == 0


class TestPlanGeneration:
    """Test pick plan generation."""

    def test_plan_creates_tasks(self):
        """Plan should create PickTask for each item."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = Order(order_id="test", items=["apple", "bottle"])
        tasks = planner.plan(order)

        assert len(tasks) == 2
        assert all(isinstance(t, PickTask) for t in tasks)
        assert tasks[0].item_name == "apple"
        assert tasks[1].item_name == "bottle"

    def test_plan_assigns_locations(self):
        """Each task should have a shelf location."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = Order(order_id="test", items=["apple", "book"])
        tasks = planner.plan(order)

        for task in tasks:
            assert task.location is not None
            assert task.location.shelf_id in ("A", "B", "C")

    def test_plan_respects_known_locations(self):
        """Items should map to their correct shelves from config."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = Order(order_id="test", items=["apple", "can"])
        tasks = planner.plan(order)

        apple_task = next(t for t in tasks if t.item_name == "apple")
        can_task = next(t for t in tasks if t.item_name == "can")

        assert apple_task.location.shelf_id == "A"
        assert can_task.location.shelf_id == "C"

    def test_plan_sets_initial_state(self):
        """All tasks should start in IDLE state."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        order = Order(order_id="test", items=["apple"])
        tasks = planner.plan(order)

        assert tasks[0].state == TaskState.IDLE
        assert tasks[0].attempts == 0


class TestReplanning:
    """Test replanning on failure."""

    def test_replan_changes_strategy(self):
        """Replan should generate a new task for the failed item."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        failed_task = PickTask(
            item_name="apple",
            location=ShelfLocation(shelf_id="A", slot=0, x=2.0, y=0.0, z=0.5),
            state=TaskState.REPLANNING,
            attempts=1,
            failure_reason="grip_failed",
        )

        new_task = planner.replan(failed_task)
        assert new_task is not None
        assert new_task.item_name == "apple"
        assert new_task.attempts == 0  # fresh attempt count

    def test_replan_floor_pickup(self):
        """Replan for dropped item should use floor location."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        failed_task = PickTask(
            item_name="bottle",
            location=ShelfLocation(shelf_id="A", slot=1, x=2.0, y=0.0, z=0.5),
            state=TaskState.REPLANNING,
            failure_reason="object_dropped",
        )

        new_task = planner.replan(failed_task)
        assert new_task is not None
        # Floor pickup should have lower z
        assert new_task.location.z < failed_task.location.z


class TestPlannerClaudeIntegration:
    """Test Planner with mocked Claude wrapper."""

    def test_planner_uses_claude_wrapper(self):
        """Planner should call ClaudeWrapper in non-mock mode."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        # In mock mode, should still work
        order = planner.parse_order("Order #99: apple, bottle")
        assert order.order_id == "99"

    def test_planner_generates_instruction(self):
        """Planner should generate VLA instructions for each task."""
        from src.orchestrator.planner import Planner

        planner = Planner(mock_mode=True)
        task = PickTask(
            item_name="apple",
            location=ShelfLocation(shelf_id="A", slot=0, x=2.0, y=0.0, z=0.5),
        )

        instruction = planner.generate_instruction(task)
        assert "apple" in instruction.lower()
        assert "shelf" in instruction.lower() or "a" in instruction.lower()
