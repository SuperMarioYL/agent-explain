"""Single-source-of-truth version lockstep test.

Asserts every user-facing version surface agrees on one version string:

  __version__ == pyproject.toml [project] version
              == uv.lock root package version
              == web/site.json content_version
              == docs/demo-results.json version
              == CHANGELOG head version
              == `agent-explain --version` CLI output

plus the sweep test below, which rejects *any* version literal in the site
content or the demo record that disagrees with __version__.

This test FAILS on the shipped v0.5.0 tag because ``web/site.json`` still
carried ``content_version: "v0.3.0"`` (two minor versions stale and carrying a
``v`` prefix no other surface uses) and the CLI had no ``--version`` flag at
all. That drift is the bug this test pins.

It also FAILS on the shipped v0.7.0 tag: the v0.6.0 lockstep covered only
``content_version``, so ``web/site.json`` ``meta.implementation_version``,
``docs/demo-results.json`` ``version`` and the ``uv.lock`` root entry were all
left at ``0.6.0`` (fix-version-surface-drift-incomplete).
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

# Matches a bare semantic version literal (no leading "v").
_VERSION_LITERAL_RE = re.compile(r"\d+\.\d+\.\d+")


def _changelog_head_version() -> str:
    text = (_REPO_ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    # First "## [x.y.z]" heading that is not [Unreleased].
    for m in re.finditer(r"^##\s*\[(\d+\.\d+\.\d+)\]", text, re.MULTILINE):
        return m.group(1)
    raise AssertionError("no versioned heading found in CHANGELOG.md")


def _uv_lock_root_version() -> str:
    """Return the locked version of this project's own (root) package."""
    text = (_REPO_ROOT / "uv.lock").read_text(encoding="utf-8")
    for block in text.split("[[package]]")[1:]:
        if re.search(r'^name = "agent-explain"$', block, re.MULTILINE):
            m = re.search(r'^version = "([^"]+)"$', block, re.MULTILINE)
            if m:
                return m.group(1)
    raise AssertionError("agent-explain root entry not found in uv.lock")


def _version_literals(path: Path) -> list[str]:
    """Every distinct x.y.z literal in *path*, sorted."""
    return sorted(set(_VERSION_LITERAL_RE.findall(path.read_text(encoding="utf-8"))))


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

    demo = json.loads(
        (_REPO_ROOT / "docs" / "demo-results.json").read_text(encoding="utf-8")
    )
    assert demo["version"] == expected, (
        "docs/demo-results.json version out of sync with __version__"
    )

    assert _uv_lock_root_version() == expected, (
        "uv.lock root package version out of sync with __version__ — re-run `uv lock`"
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


def test_site_content_and_demo_record_carry_no_stale_version() -> None:
    """No version literal anywhere in the site content or demo record may
    disagree with the shipped version.

    This is the sweep that catches the surfaces the per-field assertions above
    would miss — ``web/site.json`` ``meta.implementation_version`` and the demo
    caption, for example, which both sat at 0.6.0 on the v0.7.0 tag.
    """
    expected = __version__
    for rel in ("web/site.json", "docs/demo-results.json"):
        literals = _version_literals(_REPO_ROOT / rel)
        assert literals == [expected], (
            f"{rel} carries version literals {literals} but the package ships {expected}"
        )
