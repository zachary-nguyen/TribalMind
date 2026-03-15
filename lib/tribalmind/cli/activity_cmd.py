"""CLI command for viewing the local activity log."""

from __future__ import annotations

import json

import typer
from rich.console import Console
from rich.table import Table

console = Console()

# Action → color mapping for Rich
_ACTION_COLORS = {
    "remember": "green",
    "recall": "cyan",
    "forget": "red",
}


def activity(
    limit: int = typer.Option(
        20, "--limit", "-n",
        help="Number of recent events to show.",
    ),
    action_filter: str = typer.Option(
        "", "--action", "-a",
        help="Filter by action (remember, recall, forget).",
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j",
        help="Output as JSON.",
    ),
    clear: bool = typer.Option(
        False, "--clear",
        help="Clear the activity log.",
    ),
) -> None:
    """View recent memory activity (remember, recall, forget events).

    Shows a reverse-chronological feed of all memory interactions,
    so you can see what agents and humans have been doing.

    \b
    Examples:
        tribal activity                    # Last 20 events
        tribal activity -n 50              # Last 50 events
        tribal activity -a remember        # Only remember events
        tribal activity --json             # Machine-readable output
        tribal activity --clear            # Delete the activity log
    """
    from tribalmind.activity import clear_activity, read_activity

    if clear:
        deleted = clear_activity()
        if json_output:
            typer.echo(json.dumps({"deleted": deleted}))
        else:
            console.print(f"[green]Cleared[/green] {deleted} activity events.")
        return

    events = read_activity(limit=limit)

    if action_filter:
        events = [e for e in events if e.get("action") == action_filter]

    if json_output:
        typer.echo(json.dumps(events, indent=2))
        return

    if not events:
        console.print("[dim]No activity recorded yet.[/dim]")
        console.print("[dim]Use tribal remember / recall / forget to generate events.[/dim]")
        return

    table = Table(title="Recent Activity", show_lines=False, pad_edge=True)
    table.add_column("Time", style="dim", width=19)
    table.add_column("Action", width=10)
    table.add_column("Summary", ratio=1)
    table.add_column("#", style="dim", width=4, justify="right")
    table.add_column("Team", style="dim", width=4)

    for event in events:
        action = event.get("action", "?")
        color = _ACTION_COLORS.get(action, "white")
        timestamp = event.get("timestamp", "")
        # Format timestamp to local time
        if timestamp:
            from datetime import datetime

            try:
                dt = datetime.fromisoformat(timestamp)
                timestamp = dt.strftime("%Y-%m-%d %H:%M:%S")
            except (ValueError, TypeError):
                pass

        summary = event.get("summary", "")
        count = event.get("count", "")
        team = "yes" if event.get("team") else ""

        table.add_row(
            timestamp,
            f"[{color}]{action}[/{color}]",
            summary[:80],
            str(count) if count else "",
            team,
        )

    console.print(table)
    console.print(f"[dim]{len(events)} event(s)[/dim]")
