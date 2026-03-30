"""Shared types for the Warehouse Picker VLA system."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class TaskState(Enum):
    """State machine states for pick task lifecycle."""

    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    REPLANNING = "replanning"
    SUCCESS = "success"
    SKIPPED = "skipped"
    COMPLETED = "completed"


@dataclass
class ShelfLocation:
    """3D location of a shelf slot."""

    shelf_id: str  # e.g., "A", "B", "C"
    slot: int  # slot index on the shelf
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0


@dataclass
class PickTask:
    """A single pick-and-place task."""

    item_name: str
    location: ShelfLocation
    state: TaskState = TaskState.IDLE
    attempts: int = 0
    max_attempts: int = 3
    failure_reason: str = ""


@dataclass
class VerificationResult:
    """Result of verifying a pick action."""

    success: bool
    confidence: float = 0.0
    reason: str = ""
    suggested_action: str = ""


@dataclass
class Order:
    """A customer order with multiple items to pick."""

    order_id: str
    items: list[str] = field(default_factory=list)
    tasks: list[PickTask] = field(default_factory=list)
    completed: list[str] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)


@dataclass
class RobotAction:
    """Action output from VLA model."""

    joint_angles: list[float] = field(default_factory=list)  # 6-DOF
    gripper: float = 0.0  # 0.0 = open, 1.0 = closed
    raw_output: Any = None
