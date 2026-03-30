"""Configuration management for Warehouse Picker VLA."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CONFIGS_DIR = PROJECT_ROOT / "configs"


def load_config(name: str) -> dict[str, Any]:
    """Load a YAML config file from the configs directory."""
    path = CONFIGS_DIR / f"{name}.yaml"
    if not path.exists():
        raise FileNotFoundError(f"Config not found: {path}")
    with open(path) as f:
        return yaml.safe_load(f) or {}


def load_warehouse_config() -> dict[str, Any]:
    return load_config("warehouse")


def load_robot_config() -> dict[str, Any]:
    return load_config("robot")


def load_objects_config() -> dict[str, Any]:
    return load_config("objects")
