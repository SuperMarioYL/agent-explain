"""Tests for the per-step analyzer."""

from agent_explain.analyzer import analyze_step
from agent_explain.models import Step


def test_analyze_read_only_step():
    """A read-only step should be low risk."""
    step = Step(
        id=1,
        raw_text="Read `src/auth.py` to understand the auth flow.",
        tool_verbs=["read"],
        file_paths=["src/auth.py"],
    )
    proj = analyze_step(step)
    assert proj.step_id == 1
    assert proj.risk_class == "low"
    assert proj.est_tokens[0] > 0
    assert proj.est_tokens[1] > proj.est_tokens[0]
    assert proj.tool_call_count == 1


def test_analyze_create_step():
    """A create/write step should be medium risk."""
    step = Step(
        id=2,
        raw_text="Create `migrations/001_add_users.py` with the user schema.",
        tool_verbs=["create"],
        file_paths=["migrations/001_add_users.py"],
    )
    proj = analyze_step(step)
    assert proj.risk_class == "medium"


def test_analyze_delete_step():
    """A delete step should be high risk."""
    step = Step(
        id=3,
        raw_text="Delete `config/old_settings.json` and run the migration.",
        tool_verbs=["delete", "run"],
        file_paths=["config/old_settings.json"],
    )
    proj = analyze_step(step)
    assert proj.risk_class == "high"
    assert proj.tool_call_count == 2


def test_analyze_token_range_is_tuple():
    """est_tokens must be a tuple of two ints (a range, never a point)."""
    step = Step(id=1, raw_text="Read the docs.", tool_verbs=["read"], file_paths=[])
    proj = analyze_step(step)
    assert isinstance(proj.est_tokens, tuple)
    assert len(proj.est_tokens) == 2
    assert isinstance(proj.est_tokens[0], int)
    assert isinstance(proj.est_tokens[1], int)


def test_analyze_basis_static_when_no_local_files():
    """When no file paths resolve to local files, basis should be static."""
    step = Step(
        id=1,
        raw_text="Read `nonexistent/file.py`.",
        tool_verbs=["read"],
        file_paths=["nonexistent/file.py"],
    )
    proj = analyze_step(step)
    assert proj.basis == "static"
    assert proj.confidence == 0.40


def test_analyze_basis_sampled_when_local_files_exist(tmp_path):
    """When file paths point to real local files, basis should be sampled."""
    real_file = tmp_path / "auth.py"
    real_file.write_text("def authenticate(user, password):\n    pass\n")

    step = Step(
        id=1,
        raw_text=f"Read `{real_file}` to understand auth.",
        tool_verbs=["read"],
        file_paths=[str(real_file)],
    )
    proj = analyze_step(step)
    assert proj.basis == "sampled"
    assert proj.confidence == 0.70


def test_analyze_high_wins_over_medium_and_low():
    """If a step mentions both read and delete, risk should be high."""
    step = Step(
        id=1,
        raw_text="Read the file, then delete `old_config.py`.",
        tool_verbs=["read", "delete"],
        file_paths=["old_config.py"],
    )
    proj = analyze_step(step)
    assert proj.risk_class == "high"


def test_analyze_files_touched_carry_through():
    """files_touched should match the step's file_paths."""
    step = Step(
        id=1,
        raw_text="Edit `src/auth.py` and `src/models.py`.",
        tool_verbs=["edit"],
        file_paths=["src/auth.py", "src/models.py"],
    )
    proj = analyze_step(step)
    assert set(proj.files_touched) == {"src/auth.py", "src/models.py"}
