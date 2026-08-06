# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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

[Unreleased]: https://github.com/SuperMarioYL/agent-explain/compare/v0.3.0...HEAD
[0.3.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.3.0
[0.2.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.2.0
[0.1.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.1.0
