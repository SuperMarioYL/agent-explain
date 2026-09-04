"""Single-source-of-truth version lockstep test.

Asserts every user-facing version surface agrees on one version string:

  __version__ == pyproject.toml [project] version
              == web/site.json content_version
              == CHANGELOG head version
              == `agent-explain --version` CLI output

This test FAILS on the shipped v0.5.0 tag because ``web/site.json`` still
carried ``content_version: "v0.3.0"`` (two minor versions stale and carrying a
``v`` prefix no other surface uses) and the CLI had no ``--version`` flag at
all. That drift is the bug this test pins.
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

from typer.testing import CliRunner

from agent_explain import __version__
from agent_explain.cli import app

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _changelog_head_version() -> str:
    text = (_REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # First "## [x.y.z]" heading that is not [Unreleased].
    for m in re.finditer(r"^##\s*\[(\d+\.\d+\.\d+)\]", text, re.MULTILINE):
        return m.group(1)
    raise AssertionError("no versioned heading found in CHANGELOG.md")


def test_all_version_surfaces_agree() -> None:
    expected = __version__

    pyproject = tomllib.loads(
        (_REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    assert pyproject["project"]["version"] == expected, (
        "pyproject.toml version out of sync with __version__"
    )

    site = json.loads((_REPO_ROOT / "web" / "site.json").read_text(encoding="utf-8"))
    assert site["content_version"] == expected, (
        "web/site.json content_version out of sync with __version__"
    )

    assert _changelog_head_version() == expected, (
        "CHANGELOG head version out of sync with __version__"
    )

    runner = CliRunner()
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip() == f"agent-explain {expected}", (
        f"--version output mismatch: {result.output!r}"
    )
