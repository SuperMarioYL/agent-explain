"""Rule-based risk classification for plan steps (no LLM call in v0.1).

Deterministic rules:
  delete / move / overwrite file = high
  shell-exec / network / create / write / edit = medium
  read-only / search / inspect = low

The most dangerous verb in a step wins — a step that both reads and
deletes is classified as "high".
"""

from __future__ import annotations

import re

from .models import RiskClass

# --- High-risk patterns (destructive / irreversible) ---
_HIGH_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(?:delete|remove|rm|drop|truncate|overwrite|destroy|wipe|purge)\b",
        r"\b(?:mv|move|rename|relocate)\b",
        r"\bgit\s+(?:push|force|reset|--hard|clean|rm|rebase)\b",
        r"\b(?:format|fdisk|mkfs)\b",
        r"\bsudo\s+rm\b",
        r"\bchmod\s+[0-7]{3,4}\b",
    ]
]

# --- Medium-risk patterns (mutating / side-effecting) ---
_MEDIUM_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(?:run|execute|exec|bash|sh|shell|sudo|make)\b",
        r"\bpip\s+install\b",
        r"\bnpm\s+(?:install|i|ci)\b",
        r"\byarn\s+(?:add|install)\b",
        r"\bcargo\s+(?:build|install|run)\b",
        r"\b(?:curl|wget|fetch|requests?\.\w+|http[s]?)\b",
        r"\b(?:create|write|edit|modify|update|patch|insert|add|append)\b",
        r"\bgit\s+(?:commit|tag|merge|stash|cherry-pick)\b",
        r"\b(?:migrate|deploy|publish|release|ship|docker\s+run)\b",
        r"\b(?:install|uninstall|upgrade|downgrade)\b",
    ]
]

# --- Low-risk patterns (read-only / non-mutating) ---
_LOW_PATTERNS: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE)
    for p in [
        r"\b(?:read|view|cat|grep|find|search|list|show|inspect|analyze|check|test|lint|type|ls|head|tail)\b",
        r"\bgit\s+(?:status|log|diff|show|branch)\b",
    ]
]


def classify_risk(step_text: str) -> RiskClass:
    """Classify a step's risk level using deterministic keyword rules.

    The most dangerous verb wins. If no risky verb is detected, the step
    defaults to "low".
    """
    text_lower = step_text.lower()

    for pattern in _HIGH_PATTERNS:
        if pattern.search(text_lower):
            return "high"

    for pattern in _MEDIUM_PATTERNS:
        if pattern.search(text_lower):
            return "medium"

    # Low-risk patterns are informational — a step with only read verbs
    # and no mutating verbs is low. Otherwise default to low as well.
    return "low"


def risk_color(risk: RiskClass) -> str:
    """Return the rich color name for a risk class."""
    return {"low": "green", "medium": "yellow", "high": "red"}[risk]
