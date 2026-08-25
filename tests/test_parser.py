"""Tests for the markdown plan parser."""

from agent_explain.parser import (
    extract_file_paths,
    extract_tool_verbs,
    parse_plan,
)


# ---------- extract_file_paths ----------


def test_extract_backtick_paths():
    text = "Read `src/auth.py` and check `migrations/001_add_users.py`."
    paths = extract_file_paths(text)
    assert "src/auth.py" in paths
    assert "migrations/001_add_users.py" in paths


def test_extract_bare_path_with_extension():
    text = "Edit the file auth.py to add validation."
    paths = extract_file_paths(text)
    assert "auth.py" in paths


def test_extract_directory_paths():
    text = "Look at the `migrations/` directory."
    paths = extract_file_paths(text)
    assert "migrations/" in paths


def test_no_false_positive_version_numbers():
    text = "Upgrade to version 0.1.0 and 3.14."
    paths = extract_file_paths(text)
    assert "0.1.0" not in paths
    assert "3.14" not in paths


def test_no_false_positive_urls():
    text = "Check https://example.com/api for docs."
    paths = extract_file_paths(text)
    assert paths == []


def test_deduplicate_paths():
    text = "Read `src/auth.py`. Then edit `src/auth.py` again."
    paths = extract_file_paths(text)
    assert paths.count("src/auth.py") == 1


# ---------- extract_tool_verbs ----------


def test_extract_basic_verbs():
    text = "Create a new file and edit the auth module."
    verbs = extract_tool_verbs(text)
    assert "create" in verbs
    assert "edit" in verbs


def test_extract_verbs_case_insensitive():
    text = "DELETE the old config. Run the migration."
    verbs = extract_tool_verbs(text)
    assert "delete" in verbs
    assert "run" in verbs


def test_extract_verbs_deduplicated():
    text = "Read the file. Read it again. Read once more."
    verbs = extract_tool_verbs(text)
    assert verbs.count("read") == 1


# ---------- parse_plan: header-based ----------


HEADER_PLAN = """\
## Step 1: Read the auth module
Read `src/auth.py` to understand the current auth flow.

## Step 2: Create migration
Create `migrations/001_add_users.py` with the user schema.

## Step 3: Edit auth module
Edit `src/auth.py` to add password validation logic.

## Step 4: Delete old config and run migration
Delete `config/old_settings.json` and run `python manage.py migrate`.
"""


def test_parse_header_plan_step_count():
    plan = parse_plan(HEADER_PLAN)
    assert len(plan.steps) == 4


def test_parse_header_plan_step_ids():
    plan = parse_plan(HEADER_PLAN)
    assert [s.id for s in plan.steps] == [1, 2, 3, 4]


def test_parse_header_plan_verbs():
    plan = parse_plan(HEADER_PLAN)
    assert "read" in plan.steps[0].tool_verbs
    assert "create" in plan.steps[1].tool_verbs
    assert "edit" in plan.steps[2].tool_verbs
    assert "delete" in plan.steps[3].tool_verbs
    assert "run" in plan.steps[3].tool_verbs


def test_parse_header_plan_file_paths():
    plan = parse_plan(HEADER_PLAN)
    assert "src/auth.py" in plan.steps[0].file_paths
    assert "migrations/001_add_users.py" in plan.steps[1].file_paths
    assert "config/old_settings.json" in plan.steps[3].file_paths


# ---------- parse_plan: numbered list ----------


NUMBERED_PLAN = """\
1. Read `src/auth.py` to understand the auth flow.
2. Create `migrations/001_add_users.py` with the user schema.
3. Edit `src/auth.py` to add password validation.
"""


def test_parse_numbered_plan_step_count():
    plan = parse_plan(NUMBERED_PLAN)
    assert len(plan.steps) == 3


def test_parse_numbered_plan_step_ids():
    plan = parse_plan(NUMBERED_PLAN)
    assert [s.id for s in plan.steps] == [1, 2, 3]


def test_parse_numbered_plan_verbs():
    plan = parse_plan(NUMBERED_PLAN)
    assert "read" in plan.steps[0].tool_verbs
    assert "create" in plan.steps[1].tool_verbs


# ---------- parse_plan: paragraph fallback ----------


PARAGRAPH_PLAN = """\
Read `src/auth.py` to understand the current auth flow.

Create `migrations/001_add_users.py` with the user schema.

Delete `config/old_settings.json` and run the migration.
"""


def test_parse_paragraph_plan_step_count():
    plan = parse_plan(PARAGRAPH_PLAN)
    assert len(plan.steps) == 3


def test_parse_paragraph_plan_step_ids():
    plan = parse_plan(PARAGRAPH_PLAN)
    assert [s.id for s in plan.steps] == [1, 2, 3]


def test_parse_paragraph_plan_verbs():
    plan = parse_plan(PARAGRAPH_PLAN)
    assert "read" in plan.steps[0].tool_verbs
    assert "create" in plan.steps[1].tool_verbs
    assert "delete" in plan.steps[2].tool_verbs


# ---------- edge cases ----------


def test_parse_empty_plan():
    plan = parse_plan("")
    assert len(plan.steps) == 0


def test_parse_single_step():
    plan = parse_plan("Read `src/auth.py`.")
    assert len(plan.steps) == 1
    assert plan.steps[0].id == 1


# ---------- regression: backtick command interiors not mined (v0.4.0) ----------


def test_backtick_command_interior_not_mined_for_bare_path():
    """A `word.ext` inside a backtick-quoted command must not be mined."""
    text = "Run `python manage.py migrate` to apply the schema."
    paths = extract_file_paths(text)
    assert "manage.py" not in paths
    assert paths == []


def test_backtick_command_interior_with_trailing_ext_not_mined():
    """`node server.js --port 3000` must not yield `server.js`."""
    text = "Start the server with `node server.js --port 3000`."
    paths = extract_file_paths(text)
    assert "server.js" not in paths
    assert paths == []


def test_whole_command_with_whitespace_not_accepted_as_path():
    """A whole command with internal whitespace ending in `.ext` (e.g.
    `docker compose up app.py`) must not be accepted as a single path."""
    text = "Run `docker compose up app.py` in the project root."
    paths = extract_file_paths(text)
    assert "docker compose up app.py" not in paths
    assert "app.py" not in paths
    assert paths == []


def test_backtick_command_in_plan_step_no_files_touched():
    """A plan step whose backtick command contains a `word.ext` must not
    produce a file_paths entry for that `word.ext`."""
    plan = parse_plan(
        "## Step 1: Run migration\n"
        "Run `python manage.py migrate` to apply the schema.\n"
    )
    assert len(plan.steps) == 1
    assert "manage.py" not in plan.steps[0].file_paths


def test_real_bare_paths_outside_backticks_survive_masking():
    """Masking backtick spans must not hide real bare paths in prose
    outside the backticks."""
    text = "Run `python manage.py migrate`, then edit auth.py to fix the bug."
    paths = extract_file_paths(text)
    assert "manage.py" not in paths
    assert "auth.py" in paths


# ---------- regression: step body must not absorb non-step sections (v0.5.0) ----------


def test_header_step_does_not_absorb_non_step_section_between_steps():
    """A non-step ## Notes section between two steps must not be folded into
    the preceding step's raw_text / file_paths.

    Regression for fix-step-body-absorbs-non-step-sections: _parse_by_headers
    previously bounded each step's body at the next *step-header* only, so a
    ## Notes section (and the bare paths it mentions) was absorbed into the
    preceding step and mined by extract_file_paths.
    """
    plan = parse_plan(
        "## Step 1: Read the auth module\n"
        "Read `src/auth.py` to understand the current auth flow.\n"
        "\n"
        "## Notes\n"
        "Background prose mentioning config.py and utils.py.\n"
        "\n"
        "## Step 2: Create migration\n"
        "Create `migrations/001_add_users.py` with the user schema.\n"
    )
    assert len(plan.steps) == 2
    assert plan.steps[0].file_paths == ["src/auth.py"]
    assert "config.py" not in plan.steps[0].file_paths
    assert "utils.py" not in plan.steps[0].file_paths
    assert plan.steps[1].file_paths == ["migrations/001_add_users.py"]


def test_header_step_does_not_absorb_trailing_non_step_section():
    """A ## Notes section after the last step must not be folded into that
    last step's raw_text / file_paths."""
    plan = parse_plan(
        "## Step 1: Read the auth module\n"
        "Read `src/auth.py` to understand the current auth flow.\n"
        "\n"
        "## Notes\n"
        "Background prose mentioning config.py and utils.py.\n"
    )
    assert len(plan.steps) == 1
    assert plan.steps[0].file_paths == ["src/auth.py"]
    assert "config.py" not in plan.steps[0].file_paths
    assert "utils.py" not in plan.steps[0].file_paths


def test_numbered_step_does_not_absorb_trailing_non_step_section():
    """A ## Notes section after the last numbered item must not be folded
    into that item's raw_text / file_paths.

    Same boundary defect as _parse_by_headers (parser.py:202).
    """
    plan = parse_plan(
        "1. Read `src/auth.py` to understand the auth flow.\n"
        "2. Create `migrations/001_add_users.py` with the user schema.\n"
        "\n"
        "## Notes\n"
        "Background prose mentioning config.py and utils.py.\n"
    )
    assert len(plan.steps) == 2
    assert plan.steps[1].file_paths == ["migrations/001_add_users.py"]
    assert "config.py" not in plan.steps[1].file_paths
    assert "utils.py" not in plan.steps[1].file_paths


# ---------- regression: URL host+path not mined as file path (v0.5.0) ----------


def test_url_host_path_not_extracted_as_file_path():
    """A bare URL with a deep path (github.com/repo/blob/main/app.py) must
    not be mined as a file path — the scheme's ":" is not in the path char
    class, so _BARE_PATH_RE would otherwise start matching at the host."""
    text = "See https://github.com/repo/blob/main/app.py for the source."
    paths = extract_file_paths(text)
    assert paths == []
    assert "app.py" not in paths


def test_schemeless_domain_path_not_extracted_as_file_path():
    """A scheme-less host+path written in prose (example.com/api) must not be
    accepted as a file path by the domain-shape guard in _looks_like_path."""
    text = "See example.com/api for the endpoint."
    paths = extract_file_paths(text)
    assert paths == []


def test_bare_file_path_not_rejected_by_domain_guard():
    """A single-segment bare file (auth.py) must still be extracted — the
    domain-shape guard requires a "/" so it never fires here."""
    text = "Edit the file auth.py to add validation."
    paths = extract_file_paths(text)
    assert "auth.py" in paths

