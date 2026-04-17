"""Sprint 0 — Portfolio / Position schema tests (TDD: written before models.py)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from ria.models import Portfolio, Position


def test_position_basic_construction() -> None:
    p = Position(ticker="TSLA", quantity=30, cost_basis_usd=8400.0)
    assert p.ticker == "TSLA"
    assert p.quantity == 30
    assert p.cost_basis_usd == 8400.0


def test_position_rejects_non_string_ticker() -> None:
    with pytest.raises(ValidationError):
        Position(ticker=123, quantity=1, cost_basis_usd=100.0)


def test_position_rejects_negative_quantity() -> None:
    with pytest.raises(ValidationError):
        Position(ticker="TSLA", quantity=-5, cost_basis_usd=100.0)


def test_position_rejects_non_numeric_cost_basis() -> None:
    with pytest.raises(ValidationError):
        Position(ticker="TSLA", quantity=1, cost_basis_usd="abc")


def test_portfolio_empty_positions_allowed() -> None:
    port = Portfolio(positions=[])
    assert port.positions == []
    assert port.cash_usd == 0.0
    assert port.weights() == {}


def test_portfolio_weights_include_cash_bucket() -> None:
    port = Portfolio(
        positions=[
            Position(ticker="TSLA", quantity=30, cost_basis_usd=8400.0),
            Position(ticker="AAPL", quantity=15, cost_basis_usd=3500.0),
            Position(ticker="NVDA", quantity=3, cost_basis_usd=2100.0),
        ],
        cash_usd=500.0,
    )
    w = port.weights()
    # cash appears under the CASH key
    assert "CASH" in w
    assert set(w.keys()) == {"TSLA", "AAPL", "NVDA", "CASH"}
    # sums to ~1.0
    assert math.isclose(sum(w.values()), 1.0, abs_tol=1e-9)
    # TSLA dominates (cost_basis-based ≈ 57.9% given 8400 / 14500)
    assert w["TSLA"] > 0.5
    assert w["TSLA"] < 0.65


def test_portfolio_weights_zero_total_value_returns_empty() -> None:
    """When cost basis totals and cash are both zero, weights is empty (no div-by-zero)."""
    port = Portfolio(positions=[Position(ticker="X", quantity=0, cost_basis_usd=0.0)])
    assert port.weights() == {}


def test_portfolio_yaml_roundtrip(tmp_path: Path) -> None:
    yaml_src = """
positions:
  - ticker: TSLA
    quantity: 30
    cost_basis_usd: 8400.0
  - ticker: AAPL
    quantity: 15
    cost_basis_usd: 3500.0
  - ticker: NVDA
    quantity: 3
    cost_basis_usd: 2100.0
cash_usd: 500.0
"""
    f = tmp_path / "portfolio.yaml"
    f.write_text(yaml_src)
    raw = yaml.safe_load(f.read_text())
    port = Portfolio(**raw)
    assert len(port.positions) == 3
    assert port.cash_usd == 500.0
    tickers = [p.ticker for p in port.positions]
    assert tickers == ["TSLA", "AAPL", "NVDA"]


def test_portfolio_example_yaml_file_parses() -> None:
    """The shipped portfolio.example.yaml must parse cleanly and express TSLA concentration."""
    example = Path(__file__).resolve().parents[1] / "portfolio.example.yaml"
    assert example.exists(), f"portfolio.example.yaml missing at {example}"
    raw = yaml.safe_load(example.read_text())
    port = Portfolio(**raw)
    w = port.weights()
    assert "TSLA" in w
    # TSLA is the "50%+ concentration case" for risk-gate demos
    assert w["TSLA"] > 0.5


def test_portfolio_rejects_missing_ticker_field() -> None:
    with pytest.raises(ValidationError):
        Portfolio(positions=[{"quantity": 1, "cost_basis_usd": 100.0}])


def test_portfolio_weights_are_fractions_not_percents() -> None:
    port = Portfolio(positions=[Position(ticker="A", quantity=1, cost_basis_usd=100.0)])
    w = port.weights()
    assert 0.0 <= w["A"] <= 1.0
