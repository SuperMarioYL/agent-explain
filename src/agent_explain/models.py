"""Pydantic data models for agent-explain projections.

The core primitive is the *EXPLAIN projection* — a pre-execution cost/risk
projection of a not-yet-run plan, imported from PostgreSQL EXPLAIN
(30+ years in databases, absent from the agent-plan space until the plan
became a first-class object in 2026).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RiskClass = Literal["low", "medium", "high"]
Basis = Literal["static", "sampled"]


class Step(BaseModel):
    """A single step parsed from a coding-agent's markdown plan."""

    id: int
    raw_text: str
    tool_verbs: list[str] = Field(default_factory=list)
    file_paths: list[str] = Field(default_factory=list)


class Plan(BaseModel):
    """A parsed plan: an ordered list of steps."""

    steps: list[Step] = Field(default_factory=list)


class StepProjection(BaseModel):
    """Pre-execution projection for a single step.

    est_tokens is a *range* (low, high) — never a point estimate.
    confidence (0..1) reflects estimation certainty.
    basis: "static" = text-only analysis; "sampled" = local file sizes read.
    """

    step_id: int
    est_tokens: tuple[int, int]
    tool_call_count: int
    risk_class: RiskClass
    files_touched: list[str]
    confidence: float
    basis: Basis


class Totals(BaseModel):
    """Aggregated totals across all steps in a plan."""

    est_tokens_range: tuple[int, int]
    total_tool_calls: int
    risk_breakdown: dict[str, int]
    total_files_touched: int


class PlanProjection(BaseModel):
    """Full pre-execution projection of a plan.

    The confidence_note is the honest disclaimer: estimates are ranges,
    not point predictions; calibrate against your actuals.
    """

    steps: list[StepProjection]
    totals: Totals
    confidence_note: str
