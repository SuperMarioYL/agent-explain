# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2026-07-17

### Added
- **m1_parse_project** — parse a markdown coding-agent plan into ordered steps and emit a skeleton table (step id, raw text, tool verbs, file paths).
- **m2_estimate_risk** — per-step token estimation (tiktoken + sampled local file sizes) and rule-based risk-class; emit the full projection table with token ranges, tool-call counts, risk-class, files touched, and a confidence basis.
- **m3_calibrate_demo** — calibrate the estimator against 3-5 real captured runs, emit an accuracy note, ship a 10-minute demo and bilingual README with animated hero/atlas SVG pairs, and draft a Show HN post.
- CLI entry point `agent-explain` with rich table output and `--json` mode for piping into a pre-approval gate.
- Rule-based `risk_rules` (delete/move file = high; shell-exec / network = medium-high; read-only = low) — no LLM call in v0.1.
- Ranges + confidence basis on every projection (never a point estimate) as the direct mitigation for the hardest technical falsifier ("estimates can't beat eyeballing").

[Unreleased]: https://github.com/SuperMarioYL/agent-explain/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/SuperMarioYL/agent-explain/releases/tag/v0.1.0
