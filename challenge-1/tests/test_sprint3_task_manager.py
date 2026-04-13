"""Sprint 3: Task Manager tests (TDD — written first).

Tests for:
- State machine transitions
- Invalid transition rejection
- Max retry handling
- Full order completion flow
"""

import pytest

from src.common.types import (
    Order,
    PickTask,
    ShelfLocation,
    TaskState,
    VerificationResult,
)


class TestStateTransitions:
    """Test valid state machine transitions."""

    def test_idle_to_planning(self):
        """IDLE → PLANNING is valid."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple")
        assert task.state == TaskState.IDLE

        tm.transition(task, TaskState.PLANNING)
        assert task.state == TaskState.PLANNING

    def test_planning_to_executing(self):
        """PLANNING → EXECUTING is valid."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.PLANNING)

        tm.transition(task, TaskState.EXECUTING)
        assert task.state == TaskState.EXECUTING

    def test_executing_to_verifying(self):
        """EXECUTING → VERIFYING is valid."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.EXECUTING)

        tm.transition(task, TaskState.VERIFYING)
        assert task.state == TaskState.VERIFYING

    def test_verifying_to_success(self):
        """VERIFYING → SUCCESS is valid."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.VERIFYING)

        tm.transition(task, TaskState.SUCCESS)
        assert task.state == TaskState.SUCCESS

    def test_verifying_to_replanning(self):
        """VERIFYING → REPLANNING is valid."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.VERIFYING)

        tm.transition(task, TaskState.REPLANNING)
        assert task.state == TaskState.REPLANNING

    def test_replanning_to_executing(self):
        """REPLANNING → EXECUTING is valid (retry)."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.REPLANNING)

        tm.transition(task, TaskState.EXECUTING)
        assert task.state == TaskState.EXECUTING

    def test_replanning_to_skipped(self):
        """REPLANNING → SKIPPED is valid (max retries)."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.REPLANNING)

        tm.transition(task, TaskState.SKIPPED)
        assert task.state == TaskState.SKIPPED


class TestInvalidTransitions:
    """Test that invalid state transitions are rejected."""

    def test_idle_to_verifying_rejected(self):
        """IDLE → VERIFYING is invalid."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple")

        with pytest.raises(ValueError, match="Invalid transition"):
            tm.transition(task, TaskState.VERIFYING)

    def test_success_to_executing_rejected(self):
        """SUCCESS → EXECUTING is invalid (terminal state)."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.SUCCESS)

        with pytest.raises(ValueError, match="Invalid transition"):
            tm.transition(task, TaskState.EXECUTING)

    def test_skipped_to_planning_rejected(self):
        """SKIPPED → PLANNING is invalid (terminal state)."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.SKIPPED)

        with pytest.raises(ValueError, match="Invalid transition"):
            tm.transition(task, TaskState.PLANNING)


class TestRetryTracking:
    """Test retry count tracking."""

    def test_attempt_increments_on_execute(self):
        """Attempt count should increment when entering EXECUTING."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.PLANNING)
        assert task.attempts == 0

        tm.transition(task, TaskState.EXECUTING)
        assert task.attempts == 1

    def test_max_retry_forces_skip(self):
        """Should auto-skip when max attempts exceeded."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.REPLANNING)
        task.attempts = 3  # max_attempts default is 3

        # Should auto-transition to SKIPPED
        tm.transition(task, TaskState.EXECUTING)
        assert task.state == TaskState.SKIPPED

    def test_retry_within_limit(self):
        """Retry should work within limit."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        task = _make_task("apple", state=TaskState.REPLANNING)
        task.attempts = 1

        tm.transition(task, TaskState.EXECUTING)
        assert task.state == TaskState.EXECUTING
        assert task.attempts == 2


class TestOrderCompletion:
    """Test full order processing."""

    def test_process_order_creates_tasks(self):
        """TaskManager should create tasks from order."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        order = Order(order_id="test", items=["apple", "bottle", "book"])
        tm.load_order(order)

        assert len(tm.tasks) == 3

    def test_get_next_task(self):
        """Should return next pending task."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        order = Order(order_id="test", items=["apple", "bottle"])
        tm.load_order(order)

        next_task = tm.get_next_task()
        assert next_task is not None
        assert next_task.item_name == "apple"

    def test_no_next_task_when_all_done(self):
        """Should return None when all tasks completed or skipped."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        order = Order(order_id="test", items=["apple"])
        tm.load_order(order)

        task = tm.get_next_task()
        tm.transition(task, TaskState.PLANNING)
        tm.transition(task, TaskState.EXECUTING)
        tm.transition(task, TaskState.VERIFYING)
        tm.transition(task, TaskState.SUCCESS)

        assert tm.get_next_task() is None

    def test_is_complete(self):
        """Order should be complete when all tasks are success/skipped."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        order = Order(order_id="test", items=["apple", "bottle"])
        tm.load_order(order)

        # Complete first task
        t1 = tm.tasks[0]
        tm.transition(t1, TaskState.PLANNING)
        tm.transition(t1, TaskState.EXECUTING)
        tm.transition(t1, TaskState.VERIFYING)
        tm.transition(t1, TaskState.SUCCESS)

        assert not tm.is_complete()

        # Skip second task
        t2 = tm.tasks[1]
        tm.transition(t2, TaskState.PLANNING)
        tm.transition(t2, TaskState.EXECUTING)
        tm.transition(t2, TaskState.VERIFYING)
        tm.transition(t2, TaskState.REPLANNING)
        tm.transition(t2, TaskState.SKIPPED)

        assert tm.is_complete()

    def test_generate_report(self):
        """Should generate an order completion report."""
        from src.orchestrator.task_manager import TaskManager

        tm = TaskManager()
        order = Order(order_id="test", items=["apple", "bottle"])
        tm.load_order(order)

        # Complete apple, skip bottle
        t1 = tm.tasks[0]
        for state in [TaskState.PLANNING, TaskState.EXECUTING,
                       TaskState.VERIFYING, TaskState.SUCCESS]:
            tm.transition(t1, state)

        t2 = tm.tasks[1]
        for state in [TaskState.PLANNING, TaskState.EXECUTING,
                       TaskState.VERIFYING, TaskState.REPLANNING,
                       TaskState.SKIPPED]:
            tm.transition(t2, state)

        report = tm.generate_report()
        assert report["order_id"] == "test"
        assert report["total_items"] == 2
        assert report["completed"] == 1
        assert report["skipped"] == 1
        assert report["success_rate"] == 0.5


class TestEventCallbacks:
    """Test state transition event callbacks."""

    def test_on_transition_callback(self):
        """Callback should fire on state transition."""
        from src.orchestrator.task_manager import TaskManager

        events = []
        tm = TaskManager()
        tm.on_transition(lambda task, old, new: events.append((task.item_name, old, new)))

        task = _make_task("apple")
        tm.transition(task, TaskState.PLANNING)

        assert len(events) == 1
        assert events[0] == ("apple", TaskState.IDLE, TaskState.PLANNING)


# =============================================================================
# Helpers
# =============================================================================
def _make_task(item: str, state: TaskState = TaskState.IDLE) -> PickTask:
    """Create a PickTask for testing."""
    return PickTask(
        item_name=item,
        location=ShelfLocation(shelf_id="A", slot=0, x=2.0, y=0.0, z=0.5),
        state=state,
    )
