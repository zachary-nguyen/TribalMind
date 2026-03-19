"""CLI command for removing memories from the project knowledge base."""

from __future__ import annotations

import asyncio
import json
import sys

import typer
from rich.console import Console

from tribalmind.providers import get_provider

console = Console()


def forget(
    query: list[str] | None = typer.Argument(  # noqa: UP007
        default=None,
        help="Search query to find memories to delete.",
    ),
    memory_id: str | None = typer.Option(  # noqa: UP007
        None, "--id",
        help="Delete a specific memory by ID.",
    ),
    all_memories: bool = typer.Option(
        False, "--all",
        help="Delete ALL memories (use with caution).",
    ),
    yes: bool = typer.Option(
        False, "--yes", "-y",
        help="Skip confirmation prompt (for agent use).",
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j",
        help="Output result as JSON.",
    ),
) -> None:
    """Remove memories from the project knowledge base.

    \b
    Examples:
        tribal forget "old redis fix"           # search and confirm
        tribal forget --id mem-abc123 --yes     # delete by ID silently
        tribal forget --all --yes               # clear everything
        echo "outdated webpack tip" | tribal forget --yes
    """
    from tribalmind.config.settings import get_settings

    settings = get_settings()
    assistant_id = settings.project_assistant_id
    if not assistant_id:
        console.print("[red]No project assistant configured.[/red]")
        console.print("Run [bold]tribal init[/bold] first.")
        raise typer.Exit(1)

    try:
        # Mode 1: Delete by ID
        if memory_id:
            async def _delete_by_id() -> None:
                provider = get_provider()
                async with provider:
                    await provider.delete(memory_id)

            asyncio.run(_delete_by_id())

            from tribalmind.activity import log_activity
            log_activity(
                "forget",
                f"deleted memory {memory_id}",
                memory_id=memory_id,
                count=1,
                assistant_id=assistant_id or "",
            )

            if json_output:
                typer.echo(json.dumps({"deleted": [memory_id]}))
            else:
                console.print(f"[green]Deleted[/green] memory {memory_id}")
            return

        # Mode 2: Clear all
        if all_memories:
            if not yes:
                confirm = typer.confirm("Delete ALL memories for this project?")
                if not confirm:
                    raise typer.Abort()

            async def _clear() -> int:
                provider = get_provider()
                async with provider:
                    return await provider.clear()

            deleted = asyncio.run(_clear())

            from tribalmind.activity import log_activity
            log_activity(
                "forget",
                f"cleared all memories ({deleted})",
                count=deleted,
                assistant_id=assistant_id or "",
            )

            if json_output:
                typer.echo(json.dumps({"deleted_count": deleted}))
            else:
                console.print(f"[green]Cleared[/green] {deleted} memories.")
            return

        # Mode 3: Search and delete
        if query:
            query_text = " ".join(query)
        elif not sys.stdin.isatty():
            query_text = sys.stdin.read().strip()
        else:
            console.print(
                "[yellow]Provide a query, --id, or --all.[/yellow]"
            )
            raise typer.Exit(1)

        if not query_text:
            console.print("[yellow]Empty query.[/yellow]")
            raise typer.Exit(1)

        async def _search_and_delete() -> list[str]:
            provider = get_provider()
            async with provider:
                results = await provider.search(query_text, limit=10)
                if not results:
                    return []

                if not yes:
                    console.print(f"[dim]Found {len(results)} matching memories:[/dim]")
                    for r in results:
                        label = r.content or r.raw_content[:60]
                        console.print(f"  [{r.category}] {label}")
                    confirm = typer.confirm("Delete these memories?")
                    if not confirm:
                        raise typer.Abort()

                deleted_ids = []
                for r in results:
                    if r.memory_id:
                        await provider.delete(r.memory_id)
                        deleted_ids.append(r.memory_id)
                return deleted_ids

        deleted_ids = asyncio.run(_search_and_delete())

        from tribalmind.activity import log_activity
        log_activity(
            "forget",
            f"deleted {len(deleted_ids)} memories matching: {query_text}",
            query=query_text,
            count=len(deleted_ids),
            assistant_id=assistant_id or "",
        )

        if json_output:
            typer.echo(json.dumps({"deleted": deleted_ids}))
        elif deleted_ids:
            console.print(f"[green]Deleted[/green] {len(deleted_ids)} memories.")
        else:
            console.print("[dim]No matching memories found.[/dim]")

    except Exception as e:
        # Handle provider-specific errors
        from tribalmind.backboard.client import BackboardError

        if isinstance(e, BackboardError):
            console.print(f"[red]API error {e.status_code}:[/red] {e.detail}")
            raise typer.Exit(1)
        raise
