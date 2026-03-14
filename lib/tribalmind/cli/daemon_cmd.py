"""CLI commands for managing the TribalMind daemon."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def start(
    foreground: bool = typer.Option(
        False, "--foreground", "-f", help="Run in foreground (for debugging)"
    ),
) -> None:
    """Start the TribalMind daemon."""
    from tribalmind.daemon.manager import is_running, start_daemon, start_foreground

    if is_running():
        console.print("[yellow]Daemon is already running.[/yellow]")
        raise typer.Exit(0)

    if foreground:
        console.print("[#a78bfa]Starting daemon in foreground...[/#a78bfa]")
        start_foreground()
    else:
        start_daemon()
        console.print("[green]Daemon started.[/green]")


def stop() -> None:
    """Stop the TribalMind daemon."""
    from tribalmind.daemon.manager import is_running, stop_daemon

    if not is_running():
        console.print("[yellow]Daemon is not running.[/yellow]")
        raise typer.Exit(0)

    stop_daemon()
    console.print("[green]Daemon stopped.[/green]")


def status() -> None:
    """Show the status of the TribalMind daemon."""
    import asyncio

    from rich.panel import Panel

    from tribalmind.daemon.client import ping_daemon
    from tribalmind.daemon.manager import is_running, read_pid

    pid = read_pid()
    running = is_running()
    reachable = asyncio.run(ping_daemon()) if running else False

    if running and reachable:
        console.print(Panel(
            f"[green]Running[/green]  PID: {pid}",
            title="TribalMind Daemon",
            border_style="#6366f1",
        ))
    elif running and not reachable:
        console.print(Panel(
            f"[yellow]Process alive (PID: {pid}) but not responding on IPC port.[/yellow]",
            title="TribalMind Daemon",
            border_style="yellow",
        ))
    else:
        console.print(Panel(
            "[red]Not running[/red]",
            title="TribalMind Daemon",
            border_style="red",
        ))
