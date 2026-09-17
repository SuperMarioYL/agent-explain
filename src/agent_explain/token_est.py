"""Token estimation: tiktoken on step text + sampled local file sizes.

Agent plans lack a DB-style optimizer + table-statistics, so the
estimation basis is heuristic (static plan-text analysis + sampled local
file sizes), not optimizer-grade. We ship *ranges + confidence*, never
point estimates — the direct mitigation for the hardest technical
falsifier ("estimates can't beat eyeballing").
"""

from __future__ import annotations

import os
import sys
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

# Set when no tiktoken encoding could be loaded (offline first run — both
# cl100k_base and the gpt2 fallback download their BPE from the network) and
# counts are approximated via the bytes-per-token ratio instead.
_encoder_unavailable = False


def _warn_approx_once() -> None:
    print(
        "agent-explain: no tiktoken encoding available (offline?) — "
        "token counts are approximated (bytes/4).",
        file=sys.stderr,
    )


def _get_encoder() -> "tiktoken.Encoding | None":
    """Load the BPE encoding, or None when none can be loaded (offline).

    tiktoken downloads each encoding's BPE file on first use; an air-gapped
    machine has neither cl100k_base nor the gpt2 fallback cached, and both
    raises must degrade to the approximation instead of crashing the CLI.
    """
    global _encoder, _encoder_unavailable
    if _encoder is None and not _encoder_unavailable:
        for name in ("cl100k_base", "gpt2"):
            try:
                _encoder = tiktoken.get_encoding(name)
                break
            except Exception:
                continue
        if _encoder is None:
            _encoder_unavailable = True
            _warn_approx_once()
    return _encoder


def count_text_tokens(text: str) -> int:
    """Count tokens in *text* using tiktoken (cl100k_base encoding).

    Degrades to a bytes/4 approximation when no encoding can be loaded
    (offline): a pre-approval projection must stay usable without network,
    and the estimator already ships ranges + a confidence note.
    """
    enc = _get_encoder()
    if enc is None:
        return max(1, len(text.encode("utf-8")) // _BYTES_PER_TOKEN)
    return len(enc.encode(text))


def estimate_file_tokens(
    path: str, base_dir: str | os.PathLike[str] | None = None
) -> int | None:
    """Estimate token count for a local file based on its byte size.

    Returns None if the candidate is not a regular file or is not readable or
    does not exist. Non-regular candidates (directories, FIFOs, sockets,
    symlinks-to-dirs, broken symlinks) return None rather than their inode
    size, so only real file content is sampled. When *base_dir* is given (the
    plan file's parent), *path* is resolved against it first, then as-is
    (cwd-relative / absolute) — so sampling does not silently depend on the
    CLI's working directory. This fixes a v0.1.0 defect where a relative path
    from the plan text was resolved against the process cwd and the "sampled"
    basis degraded to "static" whenever the CLI was run from any directory
    other than the plan's.
    """
    candidates: list[str] = []
    if base_dir is not None:
        candidates.append(os.path.join(str(base_dir), path))
    candidates.append(path)
    size: int | None = None
    for candidate in candidates:
        try:
            # Guard: only sample *regular files*. A directory path — which
            # ``extract_file_paths`` extracts for backtick-quoted paths with a
            # trailing/internal slash (e.g. ``src/``, ``migrations/``) — would
            # otherwise make ``getsize`` succeed and return the directory's
            # *inode* size (64 bytes on macOS APFS, ~4096 on Linux ext4),
            # yielding a tiny positive token count that falsely flips
            # ``sampled=True`` and reports ``basis="sampled"`` (the 0.70
            # high-confidence basis) with a misleadingly small token range,
            # when no real file content was measured. ``isfile`` is False for
            # directories, FIFOs, sockets, symlinks-to-dirs, and broken
            # symlinks, so non-regular candidates fall through to ``None`` →
            # ``basis="static"``, keeping the "sampled" honesty invariant
            # ("sampled" = a real local file size was read) intact.
            if not os.path.isfile(candidate):
                continue
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
