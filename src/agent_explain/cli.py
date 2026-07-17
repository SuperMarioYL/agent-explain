"""CLI entry point for agent-explain.

Usage:
    agent-explain plan.md           # rich table projection
    agent-explain plan.md --json    # JSON for pre-approval gate
"""

from __future__ import annotations

from pathlib import Path

import typer

from .parser import parse_plan
from .projector import project
from .renderer import render_json, render_table

app = typer.Typer(
    name="agent-explain",
    help=(
        "Dry-run EXPLAIN for coding-agent plans: projects each step's "
        "tokens, tool-calls, risk-class, and files-touched before you "
        "approve."
    ),
    add_completion=False,
    no_args_is_help=True,
)


@app.command()
def explain(
    plan_file: Path = typer.Argument(
        ...,
        exists=True,
        dir_okay=False,
        readable=True,
        help="Path to the markdown plan file to project.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Output as JSON for piping into a pre-approval gate.",
    ),
) -> None:
    """Project a coding-agent plan's cost and risk before execution."""
    text = plan_file.read_text(encoding="utf-8")
    plan = parse_plan(text)
    proj = project(plan)

    if json_output:
        render_json(proj)
    else:
        render_table(proj)


def main() -> None:
    """Entry point for the ``agent-explain`` console script."""
    app()


if __name__ == "__main__":
    main()
