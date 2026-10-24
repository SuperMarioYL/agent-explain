"""fix-release-assets-never-attached (v0.8.0): the release workflow must
attach the built distributions to the GitHub Release.

``release.yml`` built ``dist/`` and uploaded it to the Actions *artifact store*
(``actions/upload-artifact@v4``) but never attached anything to the GitHub
Release, so the v0.6.0 and v0.7.0 releases carried zero assets while the
v0.5.0 release carried a mis-versioned ``agent_explain-0.4.0`` wheel. For a CLI
whose documented entry point is ``uvx agent-explain plan.md``, the Release page
is the install surface.

The workflow file is the contract here; the live asset list is verified against
the GitHub API after publishing.
"""

from __future__ import annotations

import re
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_RELEASE_YML = _ROOT / ".github" / "workflows" / "release.yml"

# Recognised ways of attaching files to a GitHub Release.
_ATTACH_TOOLS = ("gh release upload", "softprops/action-gh-release")


def _release_workflow() -> str:
    return _RELEASE_YML.read_text(encoding="utf-8")


def test_release_workflow_attaches_built_distributions_to_the_release() -> None:
    text = _release_workflow()
    assert any(tool in text for tool in _ATTACH_TOOLS), (
        "release.yml never attaches built artifacts to the GitHub Release "
        "(it only uploads them to the Actions artifact store)"
    )


def test_release_workflow_attaches_wheel_sdist_and_checksums() -> None:
    text = _release_workflow()
    # The attach step must cover every distribution the build job produces.
    assert re.search(r"dist/\*\.whl", text), "wheel not attached"
    assert re.search(r"dist/\*\.tar\.gz", text), "sdist not attached"
    assert "checksums.txt" in text, "checksums not attached"


def test_release_attach_step_is_idempotent() -> None:
    text = _release_workflow()
    # --clobber (or the action's overwrite flag) keeps a re-run, or a second
    # owner uploading the same assets, from failing the workflow.
    assert "--clobber" in text or "overwrite_files: true" in text, (
        "attach step must be idempotent so it cannot race another uploader"
    )


def test_release_workflow_can_create_the_release_when_absent() -> None:
    text = _release_workflow()
    assert "gh release create" in text or "softprops/action-gh-release" in text, (
        "attach step must create the release when it does not exist yet"
    )
