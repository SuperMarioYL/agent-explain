"""Token estimation: tiktoken on step text + sampled local file sizes.

Agent plans lack a DB-style optimizer + table-statistics, so the
estimation basis is heuristic (static plan-text analysis + sampled local
file sizes), not optimizer-grade. We ship *ranges + confidence*, never
point estimates — the direct mitigation for the hardest technical
falsifier ("estimates can't beat eyeballing").
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import tiktoken

# Empirical bytes-per-token ratio for source code.
_BYTES_PER_TOKEN = 4

# Uncertainty multiplier for the high end of the range when files are
# sampled. The agent may read more context than just the touched files.
_SAMPLED_HIGH_MULT = 1.6

# Uncertainty multiplier for text-only (static) estimates — wider range
# because we have no file-size signal.
_STATIC_HIGH_MULT = 2.0

# Encoding cache.
_encoder: "tiktoken.Encoding | None" = None


def _get_encoder() -> "tiktoken.Encoding":
    global _encoder
    if _encoder is None:
        try:
            _encoder = tiktoken.get_encoding("cl100k_base")
        except Exception:
            _encoder = tiktoken.get_encoding("gpt2")
    return _encoder


def count_text_tokens(text: str) -> int:
    """Count tokens in *text* using tiktoken (cl100k_base encoding)."""
    enc = _get_encoder()
    return len(enc.encode(text))


def estimate_file_tokens(
    path: str, base_dir: str | os.PathLike[str] | None = None
) -> int | None:
    """Estimate token count for a local file based on its byte size.

    Returns None if the file is not readable or does not exist. When *base_dir*
    is given (the plan file's parent), *path* is resolved against it first, then
    as-is (cwd-relative / absolute) — so sampling does not silently depend on
    the CLI's working directory. This fixes a v0.1.0 defect where a relative
    path from the plan text was resolved against the process cwd and the
    "sampled" basis degraded to "static" whenever the CLI was run from any
    directory other than the plan's.
    """
    candidates: list[str] = []
    if base_dir is not None:
        candidates.append(os.path.join(str(base_dir), path))
    candidates.append(path)
    size: int | None = None
    for candidate in candidates:
        try:
            size = os.path.getsize(candidate)
            break
        except (OSError, TypeError):
            continue
    if size is None or size < 0:
        return None
    return max(1, size // _BYTES_PER_TOKEN)


def estimate_step_tokens(
    step_text: str,
    file_paths: list[str],
    base_dir: str | os.PathLike[str] | None = None,
) -> tuple[tuple[int, int], str]:
    """Return ((low, high), basis) for a step's projected token usage.

    low  = text tokens only (the floor the agent must process).
    high = text tokens + sampled file content tokens (if local files exist),
           multiplied by an uncertainty factor.

    basis = "sampled" if any file size was read, else "static".

    *base_dir* (the plan file's parent) is forwarded to ``estimate_file_tokens``
    so relative paths in the plan text resolve against the plan's location,
    not the caller's working directory.
    """
    text_tokens = count_text_tokens(step_text)
    file_tokens = 0
    sampled = False

    for fp in file_paths:
        est = estimate_file_tokens(fp, base_dir=base_dir)
        if est is not None:
            file_tokens += est
            sampled = True

    low = text_tokens

    if sampled:
        high = int((text_tokens + file_tokens) * _SAMPLED_HIGH_MULT)
    else:
        high = int(text_tokens * _STATIC_HIGH_MULT)

    # Guarantee high > low.
    high = max(high, low + 1)

    basis: str = "sampled" if sampled else "static"
    return (low, high), basis
