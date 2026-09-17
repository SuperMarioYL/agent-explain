"""fix-bare-plan-invocation (v0.7.0): the documented primary invocation
`agent-explain plan.md` must run the projection directly.

Reproduces the v0.6.0 defect red: the plan file was only an argument of the
`explain` subcommand, so a bare `agent-explain <plan.md>` failed with
"No such command".
"""

from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from agent_explain.cli import app

runner = CliRunner()

PLAN = """## Step 1: create src/app.py
## Step 2: delete the database
"""


def _plan_file(tmp_path: Path) -> Path:
    p = tmp_path / "plan.md"
    p.write_text(PLAN, encoding="utf-8")
    return p


def test_bare_invocation_projects_the_plan(tmp_path):
    result = runner.invoke(app, [str(_plan_file(tmp_path))])
    assert result.exit_code == 0, result.output
    assert "pre-execution projection" in result.output
    assert "TOTAL" in result.output


def test_bare_invocation_json_emits_parseable_projection(tmp_path):
    result = runner.invoke(app, [str(_plan_file(tmp_path)), "--json"])
    assert result.exit_code == 0, result.output
    data = json.loads(result.output)
    assert data["totals"]["est_tokens_range"][0] > 0
    assert len(data["steps"]) == 2


def test_explain_prefix_form_removed_with_clear_error(tmp_path):
    # The v0.6.0 undocumented workaround prefix is gone: a bare command
    # means the plan path itself, so 'explain' is a (nonexistent) file.
    result = runner.invoke(app, ["explain", str(_plan_file(tmp_path))])
    assert result.exit_code == 2
    assert "does not exist" in result.output


def test_no_arguments_shows_usage_hint():
    result = runner.invoke(app, [])
    assert result.exit_code == 1, result.output
    assert "Usage" in result.output
    assert "--json" in result.output


def test_version_still_works():
    result = runner.invoke(app, ["--version"])
    assert result.exit_code == 0, result.output
    assert result.output.strip().startswith("agent-explain ")
