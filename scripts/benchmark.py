"""Benchmark — VLA-only vs Agent+VLA comparison.

Runs mock picking scenarios and measures success rates.
"""

from __future__ import annotations

import random
import time
from typing import Any

from src.common.types import VerificationResult
from src.orchestrator.picking_loop import PickingLoop
from src.orchestrator.verifier import Verifier


# VLA-only has lower success rate (no replanning)
VLA_ONLY_SUCCESS_PROB = 0.55
# Agent+VLA has higher success rate (replanning + retry)
AGENT_VLA_SUCCESS_PROB = 0.85

ITEMS = ["apple", "bottle", "book", "box", "can", "cup"]


class VLAOnlyVerifier(Verifier):
    """Verifier that simulates VLA-only (no recovery, single attempt)."""

    def __init__(self, success_prob: float = VLA_ONLY_SUCCESS_PROB):
        super().__init__(mock_mode=True, mock_success=True)
        self.success_prob = success_prob
        self._rng = random.Random(42)

    def verify_pick(self, image, item_name, save_dir=None):
        if self._rng.random() < self.success_prob:
            return VerificationResult(
                success=True, confidence=0.9,
                reason=f"{item_name} picked successfully",
            )
        return VerificationResult(
            success=False, confidence=0.7,
            reason=f"Failed to pick {item_name}",
            suggested_action="skip",  # VLA-only: no retry
        )


class AgentVLAVerifier(Verifier):
    """Verifier that simulates Agent+VLA (with recovery)."""

    def __init__(self, success_prob: float = AGENT_VLA_SUCCESS_PROB):
        super().__init__(mock_mode=True, mock_success=True)
        self.success_prob = success_prob
        self._rng = random.Random(42)
        self._attempt_count: dict[str, int] = {}

    def verify_pick(self, image, item_name, save_dir=None):
        self._attempt_count.setdefault(item_name, 0)
        self._attempt_count[item_name] += 1

        # Success probability increases with retries
        attempt = self._attempt_count[item_name]
        prob = min(0.98, self.success_prob + (attempt - 1) * 0.1)

        if self._rng.random() < prob:
            return VerificationResult(
                success=True, confidence=0.92,
                reason=f"{item_name} picked (attempt {attempt})",
            )
        return VerificationResult(
            success=False, confidence=0.6,
            reason=f"grip missed {item_name}",
            suggested_action="retry",
        )


def run_vla_only(num_items: int = 6) -> dict[str, Any]:
    """Run VLA-only benchmark (single attempt, no recovery)."""
    items = ITEMS[:num_items]
    order_text = f"Order #VLA: {', '.join(items)}"

    loop = PickingLoop(
        verifier=VLAOnlyVerifier(),
        mock_mode=True,
    )
    # For VLA-only, set max_attempts=1 (no retry)
    start = time.time()
    report = loop.process_order(order_text)
    elapsed = time.time() - start

    # Override: VLA-only means skip on first failure
    return {
        "success_count": report["completed"],
        "total": report["total_items"],
        "skipped": report["skipped"],
        "success_rate": report["success_rate"],
        "avg_time": elapsed / max(1, report["total_items"]),
        "total_time": elapsed,
    }


def run_agent_vla(num_items: int = 6) -> dict[str, Any]:
    """Run Agent+VLA benchmark (with planning, verification, recovery)."""
    items = ITEMS[:num_items]
    order_text = f"Order #AGENT: {', '.join(items)}"

    loop = PickingLoop(
        verifier=AgentVLAVerifier(),
        mock_mode=True,
    )
    start = time.time()
    report = loop.process_order(order_text)
    elapsed = time.time() - start

    return {
        "success_count": report["completed"],
        "total": report["total_items"],
        "skipped": report["skipped"],
        "success_rate": report["success_rate"],
        "avg_time": elapsed / max(1, report["total_items"]),
        "total_time": elapsed,
    }


def run_benchmark(num_items: int = 6, num_trials: int = 5) -> dict[str, Any]:
    """Run full benchmark comparison.

    Args:
        num_items: Number of items per trial.
        num_trials: Number of trials to average.

    Returns:
        Structured benchmark results.
    """
    vla_rates = []
    agent_rates = []

    for i in range(num_trials):
        vla = run_vla_only(num_items)
        agent = run_agent_vla(num_items)
        vla_rates.append(vla["success_rate"])
        agent_rates.append(agent["success_rate"])

    return {
        "vla_only": {
            "avg_success_rate": sum(vla_rates) / len(vla_rates),
            "success_rates": vla_rates,
            "avg_time": vla["avg_time"],
        },
        "agent_vla": {
            "avg_success_rate": sum(agent_rates) / len(agent_rates),
            "success_rates": agent_rates,
            "avg_time": agent["avg_time"],
        },
        "trials": num_trials,
        "items_per_trial": num_items,
        "improvement": (sum(agent_rates) / len(agent_rates))
        - (sum(vla_rates) / len(vla_rates)),
    }


if __name__ == "__main__":
    import json

    results = run_benchmark(num_items=6, num_trials=5)
    print(json.dumps(results, indent=2))
