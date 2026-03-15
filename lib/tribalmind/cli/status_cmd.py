"""CLI command for showing project memory status."""

from __future__ import annotations

import asyncio
import json

import typer
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

console = Console()


async def _get_memory_count(assistant_id: str) -> int:
    """Get the number of memories stored for an assistant."""
    from tribalmind.backboard.client import create_client
    from tribalmind.backboard.memory import list_memories

    async with create_client() as client:
        memories = await list_memories(client, assistant_id)
        return len(memories)


def status(
    json_output: bool = typer.Option(
        False, "--json", "-j",
        help="Output status as JSON.",
    ),
) -> None:
    """Show TribalMind project status and memory stats.

    \b
    Examples:
        tribal status
        tribal status --json
    """
    from tribalmind.backboard.client import BackboardError
    from tribalmind.config.settings import get_settings

    settings = get_settings()
    assistant_id = settings.project_assistant_id
    configured = bool(assistant_id)

    memory_count = 0
    if configured:
        try:
            memory_count = asyncio.run(_get_memory_count(assistant_id))
        except BackboardError:
            memory_count = -1  # indicate error

    info = {
        "configured": configured,
        "project_root": str(settings.project_root),
        "assistant_id": assistant_id or "",
        "memory_count": memory_count,
        "llm_provider": settings.llm_provider,
        "model_name": settings.model_name,
    }

    if json_output:
        typer.echo(json.dumps(info, indent=2))
        return

    if not configured:
        console.print("[yellow]TribalMind is not initialized for this project.[/yellow]")
        console.print("Run [bold]tribal init[/bold] to get started.")
        return

    lines = Text()
    lines.append("Project:    ", style="dim")
    lines.append(str(settings.project_root) + "\n")
    lines.append("Assistant:  ", style="dim")
    lines.append(f"{assistant_id}\n", style="#a78bfa")
    lines.append("Memories:   ", style="dim")
    if memory_count < 0:
        lines.append("(could not connect)\n", style="red")
    else:
        lines.append(f"{memory_count}\n", style="#34d399")
    lines.append("LLM:        ", style="dim")
    lines.append(f"{settings.llm_provider}/{settings.model_name}\n")

    panel = Panel(lines, title="[bold #a78bfa]TribalMind Status[/]", border_style="#6366f1")
    console.print(panel)
