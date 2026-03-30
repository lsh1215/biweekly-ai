"""Task Manager — state machine for pick task lifecycle.

Manages task state transitions, retry tracking, order completion,
and event callbacks. Implements the state machine from PRD Section 5.3:

IDLE → PLANNING → EXECUTING → VERIFYING → SUCCESS
                     │            │
                     │            ▼
                     │        REPLANNING → EXECUTING (retry)
                     │            │
                     │            ▼ (max retries)
                     │         SKIPPED
                     │
                     ▼ (all items done)
                  COMPLETED
"""

from __future__ import annotations

from typing import Any, Callable

from src.common.types import Order, PickTask, ShelfLocation, TaskState


# Valid transitions map
VALID_TRANSITIONS: dict[TaskState, set[TaskState]] = {
    TaskState.IDLE: {TaskState.PLANNING},
    TaskState.PLANNING: {TaskState.EXECUTING},
    TaskState.EXECUTING: {TaskState.VERIFYING},
    TaskState.VERIFYING: {TaskState.SUCCESS, TaskState.REPLANNING},
    TaskState.REPLANNING: {TaskState.EXECUTING, TaskState.SKIPPED},
    TaskState.SUCCESS: set(),  # terminal
    TaskState.SKIPPED: set(),  # terminal
    TaskState.COMPLETED: set(),  # terminal
}


class TaskManager:
    """Manages the lifecycle of pick tasks within an order."""

    def __init__(self):
        self.tasks: list[PickTask] = []
        self.order: Order | None = None
        self._callbacks: list[Callable[[PickTask, TaskState, TaskState], None]] = []
        self._history: list[dict[str, Any]] = []

    def load_order(self, order: Order) -> None:
        """Load an order and create tasks for each item.

        Args:
            order: Order with items to process.
        """
        self.order = order
        self.tasks = []

        for item_name in order.items:
            task = PickTask(
                item_name=item_name,
                location=ShelfLocation(shelf_id="", slot=0),
                state=TaskState.IDLE,
            )
            self.tasks.append(task)

    def transition(self, task: PickTask, new_state: TaskState) -> None:
        """Transition a task to a new state.

        Args:
            task: The task to transition.
            new_state: The target state.

        Raises:
            ValueError: If the transition is invalid.
        """
        old_state = task.state

        # Check if transition is valid
        valid_targets = VALID_TRANSITIONS.get(old_state, set())
        if new_state not in valid_targets:
            raise ValueError(
                f"Invalid transition: {old_state.value} → {new_state.value}. "
                f"Valid targets: {[s.value for s in valid_targets]}"
            )

        # Auto-skip if max attempts exceeded when trying to execute
        if new_state == TaskState.EXECUTING and task.attempts >= task.max_attempts:
            task.state = TaskState.SKIPPED
            self._record(task, old_state, TaskState.SKIPPED)
            self._fire_callbacks(task, old_state, TaskState.SKIPPED)
            return

        # Increment attempts when entering EXECUTING
        if new_state == TaskState.EXECUTING:
            task.attempts += 1

        task.state = new_state
        self._record(task, old_state, new_state)
        self._fire_callbacks(task, old_state, new_state)

    def get_next_task(self) -> PickTask | None:
        """Get the next task that needs processing.

        Returns:
            Next pending task, or None if all done.
        """
        for task in self.tasks:
            if task.state in (TaskState.IDLE, TaskState.REPLANNING):
                return task
        return None

    def is_complete(self) -> bool:
        """Check if all tasks in the order are done."""
        if not self.tasks:
            return True
        return all(
            task.state in (TaskState.SUCCESS, TaskState.SKIPPED)
            for task in self.tasks
        )

    def generate_report(self) -> dict[str, Any]:
        """Generate an order completion report.

        Returns:
            Dict with order summary stats.
        """
        completed = sum(1 for t in self.tasks if t.state == TaskState.SUCCESS)
        skipped = sum(1 for t in self.tasks if t.state == TaskState.SKIPPED)
        total = len(self.tasks)

        return {
            "order_id": self.order.order_id if self.order else "",
            "total_items": total,
            "completed": completed,
            "skipped": skipped,
            "success_rate": completed / total if total > 0 else 0.0,
            "items": [
                {
                    "name": t.item_name,
                    "state": t.state.value,
                    "attempts": t.attempts,
                    "failure_reason": t.failure_reason,
                }
                for t in self.tasks
            ],
            "history": self._history,
        }

    def on_transition(
        self, callback: Callable[[PickTask, TaskState, TaskState], None],
    ) -> None:
        """Register a callback for state transitions.

        Args:
            callback: Function(task, old_state, new_state).
        """
        self._callbacks.append(callback)

    def _fire_callbacks(
        self, task: PickTask, old_state: TaskState, new_state: TaskState,
    ) -> None:
        """Fire all registered transition callbacks."""
        for cb in self._callbacks:
            cb(task, old_state, new_state)

    def _record(
        self, task: PickTask, old_state: TaskState, new_state: TaskState,
    ) -> None:
        """Record transition in history."""
        self._history.append({
            "item": task.item_name,
            "from": old_state.value,
            "to": new_state.value,
            "attempt": task.attempts,
        })
