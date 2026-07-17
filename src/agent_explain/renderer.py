"""Render projections: rich table for humans, JSON for pre-approval gates.

The table output shows the per-step projection culminating in the aha-line
(``step 4: ~12k tokens, 3 tool-calls, risk=HIGH, files=[...]``) visible
*before* approval. The ``--json`` output is pipe-friendly for integration
into a pre-approval gate.
"""

from __future__ import annotations

from .models import PlanProjection


def render_table(proj: PlanProjection) -> None:
    """Print the projection as a rich table to stdout."""
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table

    console = Console()

    table = Table(title="agent-explain — pre-execution projection", show_lines=True)
    table.add_column("Step", style="cyan bold", no_wrap=True)
    table.add_column("Tokens (range)", justify="right", no_wrap=True)
    table.add_column("Calls", justify="right", no_wrap=True)
    table.add_column("Risk", justify="center", no_wrap=True)
    table.add_column("Files touched", overflow="fold")
    table.add_column("Basis", justify="center", no_wrap=True)

    risk_style = {"low": "green", "medium": "yellow", "high": "red"}

    for sp in proj.steps:
        lo, hi = sp.est_tokens
        style = risk_style[sp.risk_class]
        table.add_row(
            str(sp.step_id),
            f"~{lo:,}–{hi:,}",
            str(sp.tool_call_count),
            f"[{style} bold]{sp.risk_class.upper()}[/{style} bold]",
            ", ".join(sp.files_touched) if sp.files_touched else "—",
            sp.basis,
        )

    t = proj.totals
    table.add_row(
        "[bold]TOTAL[/bold]",
        f"[bold]~{t.est_tokens_range[0]:,}–{t.est_tokens_range[1]:,}[/bold]",
        f"[bold]{t.total_tool_calls}[/bold]",
        f"L:{t.risk_breakdown['low']} "
        f"M:{t.risk_breakdown['medium']} "
        f"H:{t.risk_breakdown['high']}",
        f"{t.total_files_touched} files",
        "—",
        style="dim",
    )

    console.print(table)
    console.print()
    console.print(Panel.fit(proj.confidence_note, border_style="dim"))


def render_json(proj: PlanProjection) -> None:
    """Print the projection as JSON to stdout (for pre-approval gates)."""
    print(proj.model_dump_json(indent=2))
