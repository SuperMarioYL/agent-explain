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


def test_analyze_basis_sampled_via_base_dir_not_cwd(tmp_path, monkeypatch):
    """A relative path that exists next to the plan (base_dir) but NOT in the
    caller's cwd must still sample (basis="sampled") when base_dir is passed.

    Regression for the v0.1.0 cwd-resolution bug: without base_dir, sampling
    silently degraded to "static" whenever the CLI ran outside the plan's dir.
    """
    plan_dir = tmp_path / "plan_dir"
    plan_dir.mkdir()
    real_file = plan_dir / "auth.py"
    real_file.write_text("def authenticate(user, password):\n    pass\n")

    # Run from a cwd that does NOT contain auth.py, so cwd-relative resolution
    # would miss it.
    other_dir = tmp_path / "elsewhere"
    other_dir.mkdir()
    monkeypatch.chdir(other_dir)

    step = Step(
        id=1,
        raw_text="Read `auth.py` to understand auth.",
        tool_verbs=["read"],
        file_paths=["auth.py"],
    )

    # Without base_dir (the v0.1.0 behaviour): the file is invisible from cwd.
    proj_no_base = analyze_step(step)
    assert proj_no_base.basis == "static"

    # With base_dir = the plan's directory: the file is found and sampled.
    proj_with_base = analyze_step(step, base_dir=plan_dir)
    assert proj_with_base.basis == "sampled"
    assert proj_with_base.confidence == 0.70


def test_analyze_directory_path_not_sampled(tmp_path):
    """A step referencing an *existing* directory (e.g. `` `migrations/` ``)
    must report basis="static", NOT "sampled".

    Regression for fix-directory-sampling-as-file (v0.3.0): without an
    ``os.path.isfile`` guard, ``os.path.getsize`` succeeds on a directory and
    returns its *inode* size (64 bytes on macOS APFS, ~4096 on Linux ext4).
    That yields a tiny positive token count, flips ``sampled=True``, and the
    step reports the 0.70 high-confidence "sampled" basis with a
    misleadingly small token range — when no real file content was measured.
    Only regular files may sample.
    """
    # A real, existing directory (so getsize would succeed without the fix).
    real_dir = tmp_path / "migrations"
    real_dir.mkdir()

    step = Step(
        id=1,
        raw_text="Look at the `migrations/` directory.",
        tool_verbs=["read"],
        file_paths=["migrations/"],
    )
    proj = analyze_step(step, base_dir=tmp_path)

    # The directory inode must NOT count as sampled file content.
    assert proj.basis == "static"      # NOT "sampled"
    assert proj.confidence == 0.40     # static confidence, not 0.70
    # No misleading tiny sampled range: the directory contributed zero file
    # tokens, so the projection matches the text-only (static) estimate.
    text_only = analyze_step(
        Step(
            id=1,
            raw_text=step.raw_text,
            tool_verbs=["read"],
            file_paths=[],
        ),
        base_dir=tmp_path,
    )
    assert proj.est_tokens == text_only.est_tokens
