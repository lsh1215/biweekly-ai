"""Portfolio / Position Pydantic v2 models (Sprint 0).

v1 스코프: weights()는 cost_basis_usd 기반 평가액 비율.
Sprint 2에서 실시간 fixture 가격으로 갱신하는 variant 추가 예정.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class Position(BaseModel):
    """A single long-only equity position."""

    model_config = ConfigDict(frozen=False, strict=False)

    ticker: str = Field(..., min_length=1, max_length=10, description="e.g. 'TSLA'")
    quantity: float = Field(..., ge=0.0, description="Shares held; non-negative.")
    cost_basis_usd: float = Field(..., ge=0.0, description="Total USD cost of the lot.")

    @field_validator("ticker", mode="before")
    @classmethod
    def _ticker_must_be_string(cls, v: object) -> str:
        if not isinstance(v, str):
            raise ValueError(f"ticker must be str, got {type(v).__name__}")
        return v.upper().strip()


class Portfolio(BaseModel):
    """Long-only US equity portfolio plus USD cash bucket."""

    model_config = ConfigDict(frozen=False, strict=False)

    positions: list[Position] = Field(default_factory=list)
    cash_usd: float = Field(default=0.0, ge=0.0)

    def weights(self) -> dict[str, float]:
        """Return cost-basis-weighted fractions of total book value.

        Includes a synthetic 'CASH' bucket. Returns empty dict when total
        book value is zero (avoid divide-by-zero, keeps callers defensive).
        Sum of returned values == 1.0 (unless empty).
        """
        total = sum(p.cost_basis_usd for p in self.positions) + self.cash_usd
        if total <= 0.0:
            return {}
        out: dict[str, float] = {p.ticker: p.cost_basis_usd / total for p in self.positions}
        if self.cash_usd > 0.0:
            out["CASH"] = self.cash_usd / total
        return out
