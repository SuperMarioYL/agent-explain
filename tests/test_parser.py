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
    assert not any("http" in p for p in paths)


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
