"""Per-step analysis: combines token_est, tool_count, risk_rules, file_extract.

Given a parsed Step, the analyzer produces a StepProjection with:
  - est_tokens: a range (low, high), never a point estimate
  - tool_call_count: number of distinct tool verbs detected
  - risk_class: low / medium / high (rule-based, no LLM)
  - files_touched: file paths extracted from the step text
  - confidence: 0..1 reflecting estimation certainty
  - basis: "static" (text-only) or "sampled" (file sizes read)
"""

from __future__ import annotations

from .models import Step, StepProjection
from .risk_rules import classify_risk
from .token_est import estimate_step_tokens

# Confidence values by basis — sampled (file sizes read) is more
# certain than static (text-only) because we have a real signal.
_CONFIDENCE: dict[str, float] = {
    "sampled": 0.70,
    "static": 0.40,
}


def analyze_step(step: Step) -> StepProjection:
    """Analyze a single step and produce its projection."""
    (low, high), basis = estimate_step_tokens(step.raw_text, step.file_paths)
    risk = classify_risk(step.raw_text)

    return StepProjection(
        step_id=step.id,
        est_tokens=(low, high),
        tool_call_count=len(step.tool_verbs),
        risk_class=risk,
        files_touched=step.file_paths,
        confidence=_CONFIDENCE.get(basis, 0.40),
        basis=basis,  # type: ignore[arg-type]
    )
