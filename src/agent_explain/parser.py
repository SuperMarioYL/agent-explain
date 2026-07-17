"""Parse a markdown coding-agent plan into ordered steps.

Handles three common plan formats:
  1. Header-based:  ``## Step 1: ...`` or ``## 1. ...``
  2. Numbered list: ``1. Do something``
  3. Paragraph:     plain paragraphs separated by blank lines

For each step, extracts:
  - tool_verbs:  verbs implying tool invocation (create, edit, delete, ...)
  - file_paths: file/directory paths mentioned in the step text
"""

from __future__ import annotations

import re
from pathlib import Path

from .models import Plan, Step

# --- Tool verbs ---
_TOOL_VERBS = frozenset(
    {
        "create", "write", "edit", "modify", "update", "delete", "remove",
        "move", "rename", "copy", "run", "execute", "search", "find", "grep",
        "read", "view", "install", "build", "test", "deploy", "commit",
        "push", "pull", "migrate", "lint", "format", "refactor", "list",
        "show", "inspect", "analyze", "check", "cat", "head", "tail",
        "append", "patch", "overwrite", "wipe", "purge", "drop",
    }
)

_TOOL_VERB_RE = re.compile(
    r"\b(" + "|".join(sorted(_TOOL_VERBS, key=len, reverse=True)) + r")\b",
    re.IGNORECASE,
)

# --- Step header patterns ---
# Matches: "## Step 1: ...", "## 1. ...", "### Step 2 — ...", etc.
_STEP_HEADER_RE = re.compile(
    r"^(#{1,6})\s*(?:step\s*)?(\d+)\s*[:.)\-—–]\s*(.*)$",
    re.IGNORECASE | re.MULTILINE,
)

# Numbered list: "1. text" or "1) text"
_NUM_LIST_RE = re.compile(r"^(\d+)[.)]\s+(.+)$", re.MULTILINE)

# --- File path patterns ---
_BACKTICK_RE = re.compile(r"`([^`]+)`")

_CODE_EXTENSIONS = frozenset(
    {
        ".py", ".js", ".ts", ".tsx", ".jsx", ".json", ".yaml", ".yml",
        ".md", ".txt", ".sql", ".html", ".css", ".toml", ".cfg", ".ini",
        ".sh", ".rb", ".go", ".rs", ".java", ".c", ".cpp", ".h", ".hpp",
        ".vue", ".svelte", ".xml", ".env", ".lock", ".csv", ".tsv",
        ".proto", ".gradle", ".properties", ".conf",
    }
)

# Bare path with extension (not backtick-quoted).
_BARE_PATH_RE = re.compile(
    r"(?<![`\w\-])([\w\-][\w\-./]*\.[a-zA-Z]{1,5}(?:/[\w\-./]+)*)"
)


def _looks_like_path(s: str) -> bool:
    """Return True if *s* looks like a file/directory path."""
    s = s.strip()
    if not s or len(s) < 2:
        return False
    # Skip URLs.
    if s.startswith(("http://", "https://", "ftp://")):
        return False
    # Skip version numbers like "0.1.0" or "3.14".
    if re.match(r"^\d+(\.\d+)+$", s):
        return False
    # Skip email addresses.
    if "@" in s and "/" not in s:
        return False
    # Directory path (ends with /).
    if s.endswith("/") and "/" in s[:-1]:
        return True
    # Has a slash → likely a path.
    if "/" in s:
        return True
    # Has a known code extension.
    ext = Path(s).suffix.lower()
    if ext in _CODE_EXTENSIONS:
        return True
    return False


def extract_file_paths(text: str) -> list[str]:
    """Extract file/directory paths from *text*.

    Finds backtick-quoted paths first, then bare paths with extensions.
    Deduplicates while preserving order. A bare path that is a substring
    of an already-found backtick path (e.g. ``auth.py`` inside
    ``src/auth.py``) is skipped.
    """
    paths: list[str] = []
    seen: set[str] = set()

    # 1. Backtick-quoted strings — highest confidence.
    for match in _BACKTICK_RE.finditer(text):
        candidate = match.group(1)
        if _looks_like_path(candidate) and candidate not in seen:
            seen.add(candidate)
            paths.append(candidate)

    # 2. Bare paths with extensions — skip substrings of found paths.
    for match in _BARE_PATH_RE.finditer(text):
        candidate = match.group(1)
        if not _looks_like_path(candidate) or candidate in seen:
            continue
        # Skip if candidate is a substring of an already-found path
        # (e.g. "auth.py" is part of "src/auth.py").
        if any(candidate in p for p in seen):
            continue
        seen.add(candidate)
        paths.append(candidate)

    return paths


def extract_tool_verbs(text: str) -> list[str]:
    """Extract tool-verb keywords from *text*, deduplicated, preserving order."""
    seen: set[str] = set()
    verbs: list[str] = []
    for match in _TOOL_VERB_RE.finditer(text):
        verb = match.group(1).lower()
        if verb not in seen:
            seen.add(verb)
            verbs.append(verb)
    return verbs


def _build_step(step_id: int, raw_text: str) -> Step:
    """Build a Step with extracted verbs and file paths."""
    return Step(
        id=step_id,
        raw_text=raw_text.strip(),
        tool_verbs=extract_tool_verbs(raw_text),
        file_paths=extract_file_paths(raw_text),
    )


def _parse_by_headers(text: str) -> list[Step]:
    """Parse a plan with ``## Step N: ...`` headers."""
    matches = list(_STEP_HEADER_RE.finditer(text))
    if not matches:
        return []

    steps: list[Step] = []
    for i, match in enumerate(matches):
        step_num = int(match.group(2))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        # Combine header title + body as the step's raw text.
        title = match.group(3).strip()
        raw_text = f"{title}\n{body}" if body else title
        steps.append(_build_step(step_num, raw_text))

    return steps


def _parse_by_numbered_list(text: str) -> list[Step]:
    """Parse a plan with ``1. ...`` / ``1) ...`` numbered items."""
    matches = list(_NUM_LIST_RE.finditer(text))
    if not matches:
        return []

    steps: list[Step] = []
    for i, match in enumerate(matches):
        step_num = int(match.group(1))
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        line = match.group(2).strip()
        raw_text = f"{line}\n{body}" if body else line
        steps.append(_build_step(step_num, raw_text))

    return steps


def _parse_by_paragraphs(text: str) -> list[Step]:
    """Fallback: split by blank-line-separated paragraphs."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    if not paragraphs:
        return []
    return [
        _build_step(i + 1, para) for i, para in enumerate(paragraphs)
    ]


def parse_plan(text: str) -> Plan:
    """Parse a markdown coding-agent plan into ordered steps.

    Tries header-based parsing first, then numbered list, then paragraph
    splitting as a fallback.
    """
    steps = _parse_by_headers(text)
    if steps:
        return Plan(steps=steps)

    steps = _parse_by_numbered_list(text)
    if steps:
        return Plan(steps=steps)

    steps = _parse_by_paragraphs(text)
    return Plan(steps=steps)
