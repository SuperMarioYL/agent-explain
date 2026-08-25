# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.5.0] - 2026-08-25

### Fixed
- **fix-step-body-absorbs-non-step-sections** — `_parse_by_headers` and `_parse_by_numbered_list` now bound each step's body at the next *any* markdown header line (`^#{1,6}\s`), not just the next step-header match. Previously, non-step sections appearing between or after steps (`## Notes`, `## Background`, `## References`, `## Appendix`) were folded into the preceding step's `raw_text`; the absorbed prose was then mined by `extract_file_paths`, so bare paths mentioned only in Notes/Background (e.g. `config.py`, `helpers.py`, `utils.py`) were appended to that step's `file_paths` / `files_touched`, and — for files existing next to the plan — `estimate_file_tokens` flipped the step's basis to the 0.70 "sampled" confidence. This re-broke the "sampled = a real referenced file was read" honesty invariant fixed in v0.2.0/v0.3.0/v0.4.0, and the false `files_touched` + basis propagated into the `--json` output consumed by pre-approval gates. Contiguous step behaviour is unchanged (the next step header is itself an any-header, and the body still bounds at the next recognized item). Covered by regression tests.
- **fix-url-hostpath-extracted-as-file-path** — `extract_file_paths` now masks bare URL spans (`https?://` and `ftp://` scheme + host + path) before running `_BARE_PATH_RE`, mirroring the v0.4.0 backtick-masking approach, so URL interiors (e.g. `https://example.com/api`, `https://github.com/repo/blob/main/app.py`) are never mined as bare paths. The scheme's `:` is not in the path char class, so `_BARE_PATH_RE` previously started matching at the host; the `_looks_like_path` URL guard (`startswith("http(s)://")`) never fired because the scheme was already stripped, and the `if "/" in s: return True` branch accepted the host+path. Additionally, `_looks_like_path` now rejects candidates whose first segment looks like a domain (`host.tld/path`), covering scheme-less bare host+path in prose too; single-segment files like `auth.py` are unaffected (the guard requires a `/`). Previously a bare URL in prose was added to `files_touched` / `total_files_touched` and propagated into the `--json` gate output; the shipped `test_no_false_positive_urls` only asserted `"http"` was absent (always true post-scheme-strip) so it passed while the bug shipped — it now asserts `paths == []`. Covered by regression tests.
- **fix-format-verb-false-high-risk** — `_HIGH_PATTERNS` no longer includes the bare `format` token (it matched benign "format the code/output/date" steps and, via the most-dangerous-pattern-wins rule, classified them HIGH alongside `rm -rf` / `git push --force` / `mkfs`, degrading the risk-class signal the launch hook and `--json` gate rely on). `fdisk` and `mkfs` are retained, and a scoped pattern `\bformat\s+(?:/dev/|sd[a-z]|nvme|hd|disk|drive|[a-z]:)\b` preserves HIGH coverage for direct disk-format commands; code/output/string formatting now falls through to the existing MEDIUM `run`/`make` patterns (or LOW). Covered by regression tests.

## [0.4.0] - 2026-08-12

### Fixed
- **fix-backtick-commands-extracted-as-paths** — `extract_file_paths` now masks backtick-quoted code spans before running `_BARE_PATH_RE`, so command interiors (e.g. `python manage.py migrate`, `pytest tests/`, `node server.js --port 3000`) are no longer mined for bare paths like `manage.py`/`server.js`. Separately, `_looks_like_path` now rejects candidates containing internal whitespace, so a whole command string ending in an extension (e.g. `docker compose up app.py`, `pip install -r requirements.txt`) is not accepted as a single path. Previously these false paths — the most common agent-plan input (run/test commands) — flipped `basis="sampled"` (the 0.70 high-confidence basis) and inflated `files_touched` for files the plan never referenced, re-breaking the v0.2.0/v0.3.0 "sampled honesty" invariant; the false `files_touched` + basis also propagated into the `--json` output consumed by pre-approval gates. Real bare paths in prose *outside* backticks are unaffected (masking is surgical). Covered by 5 regression tests that fail without the fix.

## [0.3.0] - 2026-08-07

### Fixed
- **fix-directory-sampling-as-file** — `estimate_file_tokens` now guards `os.path.getsize` with `os.path.isfile`, so only *regular files* are sampled. Previously, a directory path — which `extract_file_paths` extracts whenever a path is backtick-quoted with a trailing or internal slash (e.g. `` `src/` ``, `` `migrations/` ``, see `test_extract_directory_paths`) — made `getsize` succeed and return the directory's *inode* size (64 bytes on macOS APFS, ~4096 on Linux ext4), yielding a tiny positive token count that falsely flipped `sampled=True` and reported `basis="sampled"` (the 0.70 high-confidence basis) with a misleadingly small token range, when no real file content was measured. Non-regular candidates (directories, FIFOs, sockets, symlinks-to-dirs, broken symlinks) now fall through to `None` → `basis="static"`, keeping the honesty invariant ("sampled" = a real local file size was read) intact. This is distinct from the v0.2.0 `m4_fix_file_path_cwd` fix (which resolved *where* plan-referenced paths are read — plan dir vs cwd; this fixes *what* is sampled — regular files only, not directory inodes). Covered by a regression test.

## [0.2.0] - 2026-08-03

### Fixed
- **m4_fix_file_path_cwd** — file-size sampling now resolves plan-referenced relative paths against the plan file's directory (not the CLI process's working directory). Previously the "sampled" confidence basis silently degraded to "static" whenever `agent-explain` was run from any directory other than the plan's, because `estimate_file_tokens` called `os.path.getsize` on the raw relative string. The plan file's parent is now threaded through `parse_plan -> analyze_step -> estimate_step_tokens`, with a cwd/as-is fallback. Covered by a regression test.

## [0.1.0] - 2026-07-17

### Added
- **m1_parse_project** — parse a markdown coding-agent plan into ordered steps and emit a skeleton table (step id, raw text, tool verbs, file paths).
- **m2_estimate_risk** — per-step token estimation (tiktoken + sampled local file sizes) and rule-based risk-class; emit the full projection table with token ranges, tool-call counts, risk-class, files touched, and a confidence basis.
- **m3_calibrate_demo** — calibrate the estimator against 3-5 real captured runs, emit an accuracy note, ship a 10-minute demo and bilingual README with animated hero/atlas SVG pairs, and draft a Show HN post.
- CLI entry point `agent-explain` with rich table output and `--json` mode for piping into a pre-approval gate.
- Rule-based `risk_rules` (delete/move file = high; shell-exec / network = medium-high; read-only = low) — no LLM call in v0.1.
- Ranges + confidence basis on every projection (never a point estimate) as the direct mitigation for the hardest technical falsifier ("estimates can't beat eyeballing").

[Unreleased]: https://github.com/SuperMarioYL/agent-explain/compare/v0.5.0...HEAD
[0.5.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.5.0
[0.4.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.4.0
[0.3.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.3.0
[0.2.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.2.0
[0.1.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.1.0
