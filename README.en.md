<div align="right"><sub><b>EN</b>&nbsp;&nbsp;⇄&nbsp;&nbsp;<a href="./README.md">中文</a></sub></div>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/hero-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/hero-light.svg">
  <img src="./assets/hero-light.svg" width="880" alt="agent-explain — Dry-run EXPLAIN for coding-agent plans">
</picture>

<p align="center"><sub>A dry-run EXPLAIN for coding-agent plans — projects each step's tokens, tool-calls, risk-class, and files-touched before you approve, so the tired human-in-the-loop inspects at the cost layer instead of rubber-stamping.</sub></p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue" alt="MIT License"></a>
  <a href="https://github.com/SuperMarioYL/agent-explain/releases"><img src="https://img.shields.io/github/v/release/SuperMarioYL/agent-explain" alt="Latest Release"></a>
  <a href="https://github.com/SuperMarioYL/agent-explain/actions/workflows/ci.yml"><img src="https://img.shields.io/github/actions/workflow/status/SuperMarioYL/agent-explain/ci.yml?label=CI" alt="CI Status"></a>
  <img src="https://img.shields.io/badge/python-3.12+-3776AB" alt="Python 3.12+">
  <img src="https://img.shields.io/badge/Coding%20Agent-dry--run-5E5CE6" alt="Coding Agent dry-run">
  <img src="https://img.shields.io/badge/Agent-EXPLAIN-5E5CE6" alt="Agent EXPLAIN">
</p>

---

**See the cost before you approve, not after the run.** Coding agents emit a multi-step plan and immediately execute — you can't inspect at the cost layer in time. agent-explain runs an EXPLAIN pass before the first action fires.

---

<h2><img src="https://api.iconify.design/tabler:topology-star-3.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Architecture</h2>

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="./assets/atlas-dark.svg">
  <source media="(prefers-color-scheme: light)" srcset="./assets/atlas-light.svg">
  <img src="./assets/atlas-light.svg" width="880" alt="Architecture: plan.md → EXPLAIN engine → projection (table / --json)">
</picture>

Single Python process, no network calls, no LLM. `plan.md` flows through the parser (splits into steps) → analyzer (per-step token / tool-call / risk-class / files) → projector (aggregates) → renderer (rich table or JSON).

<h2><img src="https://api.iconify.design/tabler:bulb.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Why</h2>

In 2026, coding agents evolved from single-shot completions to "emit a multi-step plan, then execute" — the plan became a first-class, inspectable object. But the human-in-the-loop reviewing it can only see the semantic layer; they can't answer "how many tokens will this run burn / how many files will it touch / which step is riskiest." pydantic's [The human-in-the-loop is tired](https://pydantic.dev/articles/the-human-in-the-loop-is-tired) (HN 214↑ / 119 comments) hits this approval-fatigue pain head-on.

agent-explain imports PostgreSQL's EXPLAIN primitive (30+ years in databases) into the agent-plan space: project a plan's cost and risk *before* it runs. Unlike [cobusgreyling/loop-engineering](https://github.com/cobusgreyling/loop-engineering) (8k★, explicitly inspired by Boris Cherny) whose `loop-cost` is post-hoc accounting, agent-explain is pre-execution projection. This Agent primitive fills a gap: projects like [NousResearch/hermes-agent](https://github.com/NousResearch/hermes-agent) handle agent orchestration, but no one occupies the "preview before the loop" position. Every Coding Agent that emits a plan is a potential input — the dry-run EXPLAIN answers the cost-layer question the tired reviewer couldn't ask.

> Honest caveat: agent plans lack a DB-style optimizer + table-statistics, so the estimation basis is heuristic (static text analysis + sampled local file sizes), not optimizer-grade. That's why we ship **ranges + confidence**, never point estimates — the direct mitigation for the hardest technical falsifier ("estimates can't beat eyeballing").

### vs loop-engineering

| Axis | agent-explain | [loop-engineering](https://github.com/cobusgreyling/loop-engineering) |
|---|---|---|
| Timeline | pre-execution projection | ✓ post-hoc accounting (loop-cost) |
| Cost preview | ✓ token range + tool-call count | — |
| Risk class | ✓ rule-based risk-class | — |
| File tracking | ✓ files touched | partial (session replay) |
| Agent orchestration | — (single-plan projection) | ✓ orchestration-first |
| LLM dependency | — rules-only, no LLM | ✓ |

<h2><img src="https://api.iconify.design/tabler:rocket.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Install</h2>

```bash
# No install needed — uv auto-pulls
uvx agent-explain plan.md
```

<h2><img src="https://api.iconify.design/tabler:rocket.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Quickstart</h2>

```bash
# 1. Write a coding-agent multi-step plan (or use examples/plan.md)
cat examples/plan.md

# 2. Run EXPLAIN — get the per-step projection table
uvx agent-explain examples/plan.md

# 3. JSON output, pipe into a pre-approval gate
agent-explain examples/plan.md --json
```

<details>
<summary>Sample output</summary>

```
                    agent-explain — pre-execution projection
┏━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━━━━┳━━━━━━━━┓
┃ Step  ┃ Tokens (range) ┃ Calls ┃  Risk   ┃ Files touched      ┃ Basis  ┃
┡━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━━━━╇━━━━━━━━┩
│ 1     │         ~26–52 │     1 │   LOW   │ src/auth.py        │ static │
│ 2     │         ~33–66 │     1 │ MEDIUM  │ migrations/001.py  │ static │
│ 3     │         ~32–64 │     3 │ MEDIUM  │ src/auth.py        │ static │
│ 4     │         ~38–76 │     3 │  HIGH   │ config/old.json    │ static │
│ 5     │         ~26–52 │     1 │ MEDIUM  │ tests/test_auth.py │ static │
│ TOTAL │       ~155–310 │     9 │ L:1 M:3 │ 5 files            │   —    │
└───────┴────────────────┴───────┴─────────┴────────────────────┴────────┘

Estimates are ranges; calibrate against your actuals.
```

</details>

<h2><img src="https://api.iconify.design/tabler:terminal-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Usage</h2>

```bash
# Project a plan, output rich table
agent-explain path/to/plan.md

# JSON output, pipe into a pre-approval gate or jq filter
agent-explain path/to/plan.md --json | jq '.totals'

# Filter for high-risk steps only
agent-explain path/to/plan.md --json | jq '.steps[] | select(.risk_class == "high")'

# Use in an approval hook
agent-explain .claude/plan.md --json | pre-approval-gate
```

More example plans in [`examples/`](./examples/).

<h2><img src="https://api.iconify.design/tabler:photo.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Demo</h2>

![demo](assets/demo.gif)

<h2><img src="https://api.iconify.design/tabler:map-2.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Roadmap</h2>

- [x] **m1** — Parse a markdown plan into ordered steps; emit skeleton table (step id, raw text, tool verbs, file paths)
- [x] **m2** — Per-step token estimation (tiktoken + sampled local file sizes) + rule-based risk-class; emit full projection table with token ranges and confidence basis
- [ ] **m3** — Calibrate estimator against 3-5 real captured runs; emit accuracy note
- [ ] Cross-agent support (Cursor/Codex native plan formats)
- [ ] Calibration store / loop-cost training-signal loop
- [ ] IDE integration / MCP server

<h2><img src="https://api.iconify.design/tabler:share.svg?color=%230071E3&width=24" height="22" align="absmiddle" alt=""> Share this</h2>

```
agent-explain — the dry-run EXPLAIN for your Coding Agent's plan. Projects token ranges, tool-calls, and risk-class per step before you approve, not after. https://github.com/SuperMarioYL/agent-explain
```

After pushing, set topics:

```bash
gh repo edit SuperMarioYL/agent-explain --add-topic agent --add-topic coding-agent --add-topic explain --add-topic dry-run --add-topic cli
```

## Contributing

File an [Issue](https://github.com/SuperMarioYL/agent-explain/issues) or open a [PR](https://github.com/SuperMarioYL/agent-explain/pulls).

<p align="center"><sub><a href="./LICENSE">MIT</a> © 2026 SuperMarioYL</sub></p>
