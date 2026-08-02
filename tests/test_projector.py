"""Tests for the projector (plan-level aggregation)."""

from agent_explain.models import Plan, Step
from agent_explain.projector import project


def _make_plan() -> Plan:
    """Build a 4-step plan mirroring the plan.md aha-line scenario."""
    return Plan(
        steps=[
            Step(
                id=1,
                raw_text="Read `src/auth.py` to understand the current auth flow.",
                tool_verbs=["read"],
                file_paths=["src/auth.py"],
            ),
            Step(
                id=2,
                raw_text="Create `migrations/001_add_users.py` with the user schema.",
                tool_verbs=["create"],
                file_paths=["migrations/001_add_users.py"],
            ),
            Step(
                id=3,
                raw_text="Edit `src/auth.py` to add password validation logic.",
                tool_verbs=["edit"],
                file_paths=["src/auth.py"],
            ),
            Step(
                id=4,
                raw_text=(
                    "Delete `config/old_settings.json` and run "
                    "`python manage.py migrate`."
                ),
                tool_verbs=["delete", "run"],
                file_paths=["config/old_settings.json"],
            ),
        ]
    )


def test_project_step_count():
    proj = project(_make_plan())
    assert len(proj.steps) == 4


def test_project_totals_token_range():
    proj = project(_make_plan())
    t = proj.totals
    assert t.est_tokens_range[0] > 0
    assert t.est_tokens_range[1] > t.est_tokens_range[0]
    # Sum of lows <= total low; sum of highs >= total high.
    sum_low = sum(sp.est_tokens[0] for sp in proj.steps)
    sum_high = sum(sp.est_tokens[1] for sp in proj.steps)
    assert t.est_tokens_range[0] == sum_low
    assert t.est_tokens_range[1] == sum_high


def test_project_totals_tool_calls():
    proj = project(_make_plan())
    t = proj.totals
    # read(1) + create(1) + edit(1) + delete+run(2) = 5
    assert t.total_tool_calls == 5


def test_project_risk_breakdown():
    proj = project(_make_plan())
    t = proj.totals
    # step 1 = low, step 2 = medium, step 3 = medium, step 4 = high
    assert t.risk_breakdown["low"] == 1
    assert t.risk_breakdown["medium"] == 2
    assert t.risk_breakdown["high"] == 1


def test_project_files_touched_dedup():
    proj = project(_make_plan())
    t = proj.totals
    # src/auth.py is touched by steps 1 and 3 → dedup to 3 distinct files.
    assert t.total_files_touched == 3


def test_project_confidence_note_present():
    proj = project(_make_plan())
    assert proj.confidence_note
    assert "calibrate" in proj.confidence_note.lower()


def test_project_empty_plan():
    proj = project(Plan(steps=[]))
    assert len(proj.steps) == 0
    assert proj.totals.est_tokens_range == (0, 0)
    assert proj.totals.total_tool_calls == 0
    assert "No steps" in proj.confidence_note


def test_project_step_ids_sequential():
    proj = project(_make_plan())
    assert [sp.step_id for sp in proj.steps] == [1, 2, 3, 4]


def test_project_base_dir_enables_sampling_from_other_cwd(tmp_path, monkeypatch):
    """project(plan, base_dir=...) threads the plan dir to the estimator so a
    relative path that exists next to the plan is sampled even when the CLI
    runs from an unrelated cwd. Regression for the v0.1.0 cwd-resolution bug.
    """
    plan_dir = tmp_path / "plan_dir"
    plan_dir.mkdir()
    (plan_dir / "auth.py").write_text("def authenticate():\n    pass\n")

    monkeypatch.chdir(tmp_path)  # cwd has no auth.py

    plan = Plan(
        steps=[
            Step(
                id=1,
                raw_text="Read `auth.py`.",
                tool_verbs=["read"],
                file_paths=["auth.py"],
            ),
        ]
    )

    without_base = project(plan)
    assert without_base.steps[0].basis == "static"

    with_base = project(plan, base_dir=plan_dir)
    assert with_base.steps[0].basis == "sampled"
