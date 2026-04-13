"""Planner — parses orders, generates pick plans, replans on failure.

Uses claude -p (via ClaudeWrapper) for intelligent planning,
with mock mode for testing.
"""

from __future__ import annotations

import re
import uuid
from typing import Any

from src.common.config import load_objects_config, load_warehouse_config
from src.common.types import Order, PickTask, ShelfLocation, TaskState
from src.orchestrator.claude_wrapper import ClaudeWrapper


# Build item→shelf mapping from config
def _build_item_locations() -> dict[str, ShelfLocation]:
    """Build item name → ShelfLocation mapping from configs."""
    objects_cfg = load_objects_config()
    warehouse_cfg = load_warehouse_config()

    # Build shelf position lookup
    shelf_positions: dict[str, dict[str, float]] = {}
    for shelf in warehouse_cfg["warehouse"]["shelves"]:
        shelf_positions[shelf["id"]] = shelf["position"]

    locations: dict[str, ShelfLocation] = {}
    for obj in objects_cfg["objects"]:
        shelf_id = obj["shelf"]
        slot = obj["slot"]
        pos = shelf_positions.get(shelf_id, {"x": 0, "y": 0, "z": 0})
        # Offset z for shelf height (slot-based)
        z = 0.5 + slot * 0.3
        locations[obj["name"]] = ShelfLocation(
            shelf_id=shelf_id,
            slot=slot,
            x=pos["x"],
            y=pos["y"],
            z=z,
        )

    return locations


class Planner:
    """Orchestrator planner — order parsing, plan generation, replanning."""

    # Known items and their locations (loaded from config)
    KNOWN_ITEMS = [
        "apple", "bottle", "book", "box", "can", "cup",
    ]

    def __init__(self, mock_mode: bool = False, claude: ClaudeWrapper | None = None):
        self.mock_mode = mock_mode
        self.claude = claude or ClaudeWrapper(mock_mode=mock_mode)
        self._item_locations = _build_item_locations()

    def parse_order(self, order_text: str) -> Order:
        """Parse a natural language order into an Order object.

        Args:
            order_text: Natural language order string.

        Returns:
            Order with order_id and items list.
        """
        if not order_text.strip():
            return Order(order_id=str(uuid.uuid4())[:8], items=[])

        # Extract order ID
        order_id = self._extract_order_id(order_text)

        # Extract items
        items = self._extract_items(order_text)

        return Order(order_id=order_id, items=items)

    def plan(self, order: Order) -> list[PickTask]:
        """Generate a pick plan for an order.

        Args:
            order: Order with items to pick.

        Returns:
            List of PickTasks with locations assigned.
        """
        tasks = []
        for item_name in order.items:
            location = self._get_item_location(item_name)
            task = PickTask(
                item_name=item_name,
                location=location,
                state=TaskState.IDLE,
                attempts=0,
            )
            tasks.append(task)

        order.tasks = tasks
        return tasks

    def replan(self, failed_task: PickTask) -> PickTask:
        """Generate a new plan for a failed task.

        Args:
            failed_task: The task that failed.

        Returns:
            New PickTask with adjusted strategy.
        """
        reason = failed_task.failure_reason.lower()

        if "drop" in reason or "fall" in reason:
            # Object dropped — pick from floor
            new_location = ShelfLocation(
                shelf_id=failed_task.location.shelf_id,
                slot=failed_task.location.slot,
                x=failed_task.location.x,
                y=failed_task.location.y,
                z=0.1,  # floor level
            )
        else:
            # Default: retry from same location
            new_location = ShelfLocation(
                shelf_id=failed_task.location.shelf_id,
                slot=failed_task.location.slot,
                x=failed_task.location.x,
                y=failed_task.location.y,
                z=failed_task.location.z,
            )

        return PickTask(
            item_name=failed_task.item_name,
            location=new_location,
            state=TaskState.IDLE,
            attempts=0,
        )

    def generate_instruction(self, task: PickTask) -> str:
        """Generate a natural language instruction for the VLA.

        Args:
            task: PickTask to generate instruction for.

        Returns:
            Natural language instruction string.
        """
        shelf = task.location.shelf_id
        item = task.item_name

        if task.location.z < 0.2:
            return f"pick the {item} from the floor near shelf {shelf}"

        return f"pick the {item} from shelf {shelf}"

    def _extract_order_id(self, text: str) -> str:
        """Extract order ID from text."""
        match = re.search(r'#(\w+)', text)
        if match:
            return match.group(1)
        return str(uuid.uuid4())[:8]

    def _extract_items(self, text: str) -> list[str]:
        """Extract item names from order text."""
        items = []
        text_lower = text.lower()
        for item in self.KNOWN_ITEMS:
            if item in text_lower:
                items.append(item)

        # If no known items found, try splitting by comma
        if not items:
            # Remove order prefix
            cleaned = re.sub(r'(order|주문)\s*#?\w*:?\s*', '', text, flags=re.IGNORECASE)
            parts = [p.strip().lower() for p in cleaned.split(',') if p.strip()]
            # Filter to known items
            for part in parts:
                for item in self.KNOWN_ITEMS:
                    if item in part:
                        items.append(item)
                        break

        return items

    def _get_item_location(self, item_name: str) -> ShelfLocation:
        """Look up an item's location from config."""
        if item_name in self._item_locations:
            loc = self._item_locations[item_name]
            # Return a copy
            return ShelfLocation(
                shelf_id=loc.shelf_id,
                slot=loc.slot,
                x=loc.x,
                y=loc.y,
                z=loc.z,
            )
        # Unknown item — default to shelf A
        return ShelfLocation(shelf_id="A", slot=0, x=2.0, y=0.0, z=0.5)
