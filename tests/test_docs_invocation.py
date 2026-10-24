"""fix-docs-explain-subcommand-invocation-drift (v0.8.0): every documented
invocation must match the shipped CLI.

v0.7.0 removed the ``explain`` subcommand — the projection became the app's
single command (``src/agent_explain/cli.py``), and the CHANGELOG marks the
removal as breaking. The README Usage block, the linked reproduction script,
the recorded demo tape and the recorded demo output were never updated, so
every documented invocation of the form ``agent-explain explain <plan>`` now
exits 2 with ``File 'explain' does not exist``.

These tests pin the documented surface to the real CLI: no doc surface may
use the removed prefix, and the command recorded in ``docs/demo-results.json``
must actually run and reproduce the recorded projection.
"""

from __future__ import annotations

import json
import shlex
from pathlib import Path

from typer.testing import CliRunner

from agent_explain.cli import app

_ROOT = Path(__file__).resolve().parent.parent

# Documented invocation surfaces — including the website content package,
# which renders its demo command on the live product page. CHANGELOG.md is
# deliberately excluded: its v0.7.0 entry documents the removal of the prefix
# and must keep saying so.
_DOC_SURFACES = (
    "README.md",
    "README.en.md",
    "docs/demo.sh",
    "docs/demo.tape",
    "docs/demo-results.json",
    "web/site.json",
)

_REMOVED_PREFIX = "agent-explain explain"


def test_no_doc_surface_uses_the_removed_explain_subcommand() -> None:
    offenders = []
    for rel in _DOC_SURFACES:
        for lineno, line in enumerate(
            (_ROOT / rel).read_text(encoding="utf-8").splitlines(), start=1
        ):
            if _REMOVED_PREFIX in line:
                offenders.append(f"{rel}:{lineno}: {line.strip()}")
    assert offenders == [], (
        "documented invocations still use the `explain` subcommand removed in "
        "v0.7.0 (they exit 2 with \"File 'explain' does not exist\"):\n"
        + "\n".join(offenders)
    )


def _without_token_estimates(projection: dict) -> dict:
    """Drop the tiktoken-derived fields so the comparison is encoder-independent.

    Token counts come from tiktoken when an encoding can be loaded and from the
    bytes/4 approximation when it cannot (the v0.7.0 offline degradation), so an
    air-gapped machine legitimately produces different numbers. Everything else
    in the record — risk classes, tool-call counts, files touched, basis,
    confidence, note — is encoder-independent.
    """
    return {
        "steps": [
            {k: v for k, v in step.items() if k != "est_tokens"}
            for step in projection["steps"]
        ],
        "totals": {
            k: v for k, v in projection["totals"].items() if k != "est_tokens_range"
        },
        "confidence_note": projection["confidence_note"],
    }


def test_recorded_demo_command_runs_and_reproduces_the_recorded_projection(
    tmp_path, monkeypatch
) -> None:
    monkeypatch.chdir(_ROOT)
    record = json.loads(
        (_ROOT / "docs" / "demo-results.json").read_text(encoding="utf-8")
    )
    recorded = record["steps"][0]

    # The recorded command is the full shell line; drop the console-script name.
    argv = shlex.split(recorded["command"])[1:]
    result = CliRunner().invoke(app, argv)
    assert result.exit_code == 0, result.output

    actual = json.loads(result.output)
    expected = json.loads(recorded["output"])
    assert _without_token_estimates(actual) == _without_token_estimates(expected)

    # The recorded token ranges must still be honest ranges.
    for step in actual["steps"]:
        low, high = step["est_tokens"]
        assert 0 < low < high
