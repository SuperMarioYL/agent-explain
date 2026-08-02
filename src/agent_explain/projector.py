"""Aggregate per-step projections into a PlanProjection.

The projector runs the analyzer on each step, then rolls up totals:
  - total token range (sum of lows to sum of highs)
  - total tool-call count
  - risk breakdown (count per class)
  - total distinct files touched
  - a confidence note that honestly states the estimation basis
"""

from __future__ import annotations

import os

from .analyzer import analyze_step
from .models import Plan, PlanProjection, StepProjection, Totals


def project(
    plan: Plan, base_dir: str | os.PathLike[str] | None = None
) -> PlanProjection:
    """Project an entire plan: analyze each step, aggregate totals.

    *base_dir* (the plan file's parent) is forwarded to each step's analyzer
    so relative file paths resolve against the plan's location, not the CLI's
    working directory — keeping the "sampled" confidence basis stable across
    invocation directories.
    """
    step_projections: list[StepProjection] = [
        analyze_step(s, base_dir=base_dir) for s in plan.steps
    ]

    if not step_projections:
        return PlanProjection(
            steps=[],
            totals=Totals(
                est_tokens_range=(0, 0),
                total_tool_calls=0,
                risk_breakdown={"low": 0, "medium": 0, "high": 0},
                total_files_touched=0,
            ),
            confidence_note="No steps parsed from the plan.",
        )

    total_low = sum(sp.est_tokens[0] for sp in step_projections)
    total_high = sum(sp.est_tokens[1] for sp in step_projections)
    total_calls = sum(sp.tool_call_count for sp in step_projections)

    all_files: set[str] = set()
    for sp in step_projections:
        all_files.update(sp.files_touched)

    risk_breakdown = {"low": 0, "medium": 0, "high": 0}
    for sp in step_projections:
        risk_breakdown[sp.risk_class] += 1

    any_sampled = any(sp.basis == "sampled" for sp in step_projections)
    all_sampled = all(sp.basis == "sampled" for sp in step_projections)

    if all_sampled:
        note = (
            "Estimates are ranges; calibrate against your actuals. "
            "Local file sizes were sampled for all steps."
        )
    elif any_sampled:
        note = (
            "Estimates are ranges; calibrate against your actuals. "
            "Some local file sizes were sampled; others are text-only."
        )
    else:
        note = (
            "Estimates are ranges; calibrate against your actuals. "
            "Text-only basis — no local files were sampled."
        )

    totals = Totals(
        est_tokens_range=(total_low, total_high),
        total_tool_calls=total_calls,
        risk_breakdown=risk_breakdown,
        total_files_touched=len(all_files),
    )

    return PlanProjection(
        steps=step_projections, totals=totals, confidence_note=note
    )
