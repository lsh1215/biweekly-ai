"""A/B Comparison Visualization — matplotlib bar chart.

Generates a comparison chart between VLA-only and Agent+VLA performance.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any


def generate_chart(
    vla_data: dict[str, Any],
    agent_data: dict[str, Any],
    output_path: str,
) -> None:
    """Generate a comparison bar chart.

    Args:
        vla_data: Dict with success_rate, avg_time.
        agent_data: Dict with success_rate, avg_time.
        output_path: Path to save the PNG chart.
    """
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    import numpy as np

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Success Rate comparison
    methods = ["VLA-Only", "Agent+VLA"]
    rates = [vla_data["success_rate"] * 100, agent_data["success_rate"] * 100]
    colors = ["#FF6B6B", "#4ECDC4"]
    bars1 = ax1.bar(methods, rates, color=colors, width=0.5, edgecolor="black", linewidth=0.8)
    ax1.set_ylabel("Success Rate (%)", fontsize=12)
    ax1.set_title("Pick Success Rate", fontsize=14, fontweight="bold")
    ax1.set_ylim(0, 105)
    ax1.axhline(y=80, color="gray", linestyle="--", alpha=0.5, label="Target (80%)")
    ax1.legend()
    for bar, rate in zip(bars1, rates):
        ax1.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 1.5,
            f"{rate:.1f}%",
            ha="center", va="bottom", fontweight="bold", fontsize=11,
        )

    # Avg Time comparison
    times = [vla_data["avg_time"], agent_data["avg_time"]]
    bars2 = ax2.bar(methods, times, color=colors, width=0.5, edgecolor="black", linewidth=0.8)
    ax2.set_ylabel("Avg Time per Item (s)", fontsize=12)
    ax2.set_title("Processing Time", fontsize=14, fontweight="bold")
    for bar, t in zip(bars2, times):
        ax2.text(
            bar.get_x() + bar.get_width() / 2.0,
            bar.get_height() + 0.02,
            f"{t:.2f}s",
            ha="center", va="bottom", fontweight="bold", fontsize=11,
        )

    improvement = rates[1] - rates[0]
    fig.suptitle(
        f"Warehouse Picker: VLA-Only vs Agent+VLA  (Agent improves by +{improvement:.1f}%)",
        fontsize=13, fontweight="bold", y=1.02,
    )

    plt.tight_layout()
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output_path, dpi=150, bbox_inches="tight")
    plt.close(fig)


if __name__ == "__main__":
    from scripts.benchmark import run_benchmark

    results = run_benchmark(num_items=6, num_trials=5)
    output = "docs/assets/ab_comparison.png"
    generate_chart(
        results["vla_only"],
        results["agent_vla"],
        output,
    )
    print(f"Chart saved to {output}")
