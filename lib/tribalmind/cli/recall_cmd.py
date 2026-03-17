"""CLI command for searching project memory via semantic search."""

from __future__ import annotations

import asyncio
import json
import sys

import typer
from rich.console import Console
from rich.table import Table

console = Console()

VALID_CATEGORIES = frozenset({
    "fix", "convention", "architecture", "context", "decision", "tip", "workflow",
})


def _filter_by_category(results: list, categories: set[str]) -> list:
    """Filter memory entries to only those matching *categories*."""
    return [r for r in results if r.category in categories]


async def _list_all(assistant_id: str) -> list:
    """List all memories for an assistant (no search, no RAG cost)."""
    from tribalmind.backboard.client import create_client
    from tribalmind.backboard.memory import list_memories

    async with create_client() as client:
        return await list_memories(client, assistant_id)


async def _search(assistant_id: str, query: str, limit: int) -> list:
    """Search memories for a single assistant."""
    from tribalmind.backboard.client import create_client
    from tribalmind.backboard.memory import search_memories

    async with create_client() as client:
        return await search_memories(client, assistant_id, query, limit=limit)


async def _search_all_assistants(query: str, limit: int) -> list[tuple[str, list]]:
    """Search memories across ALL assistants in the account.

    Returns a list of (assistant_name, results) tuples.
    """
    from tribalmind.backboard.assistants import list_assistants
    from tribalmind.backboard.client import create_client
    from tribalmind.backboard.memory import search_memories

    async with create_client() as client:
        assistants = await list_assistants(client)
        all_results: list[tuple[str, list]] = []
        for a in assistants:
            aid = a.get("assistant_id", a.get("id", ""))
            name = a.get("name", aid)
            if not aid:
                continue
            try:
                results = await search_memories(client, aid, query, limit=limit)
                if results:
                    all_results.append((name, results))
            except Exception:
                # Skip assistants that fail (e.g. no memories)
                continue
        return all_results


def _memory_to_dict(r) -> dict:
    """Convert a MemoryEntry to a JSON-serializable dict."""
    return {
        "memory_id": r.memory_id,
        "category": r.category,
        "subject": r.subject,
        "content": r.content,
    }


def _memory_to_search_dict(r) -> dict:
    """Convert a MemoryEntry to a JSON-serializable dict with relevance."""
    d = _memory_to_dict(r)
    d["relevance"] = r.relevance_score
    return d


def _make_table(title: str, *, show_relevance: bool = False) -> Table:
    """Create a styled table for memory display."""
    table = Table(title=title, show_lines=True)
    table.add_column("Cat", style="#a78bfa", width=12)
    table.add_column("Subject", style="#34d399", width=18)
    table.add_column("Content", style="white", ratio=1)
    if show_relevance:
        table.add_column("Rel", style="dim", width=6, justify="right")
    return table


def _add_row(table: Table, r, *, show_relevance: bool = False) -> None:
    """Add a memory entry as a row to a table."""
    cols = [
        r.category or "-",
        r.subject or "-",
        r.content or r.raw_content[:80],
    ]
    if show_relevance:
        cols.append(f"{r.relevance_score:.0%}" if r.relevance_score else "-")
    table.add_row(*cols)


def recall(
    query: list[str] | None = typer.Argument(  # noqa: UP007
        default=None,
        help="Search query (or pipe via stdin).",
    ),
    limit: int = typer.Option(
        10, "--limit", "-n",
        help="Maximum number of results.",
    ),
    json_output: bool = typer.Option(
        False, "--json", "-j",
        help="Output results as JSON (for agent consumption).",
    ),
    list_all: bool = typer.Option(
        False, "--list", "-l",
        help="List all memories (no search query needed, no RAG cost).",
    ),
    search_all: bool = typer.Option(
        False, "--all", "-a",
        help="Search across ALL repos/assistants in the account (cross-repo).",
    ),
    category: str | None = typer.Option(  # noqa: UP007
        None, "--category", "-c",
        help="Filter by category (comma-separated). "
             "Values: fix, convention, architecture, context, decision, tip, workflow.",
    ),
) -> None:
    """Search project memory by semantic similarity.

    Returns the most relevant memories matching your query.
    Use --list to browse all stored memories without a search query.
    Use --all to search across every repo in your Backboard account.

    \b
    Examples:
        tribal recall "numpy compatibility"
        tribal recall "redis connection errors" --json
        tribal recall "database migration" --limit 5
        tribal recall --list                 # browse all memories
        tribal recall --all "auth token"     # search all repos
        echo "webpack build failing" | tribal recall --json
    """
    from tribalmind.backboard.client import BackboardError
    from tribalmind.config.settings import get_settings

    settings = get_settings()

    # Parse and validate --category
    cat_filter: set[str] | None = None
    if category:
        cat_filter = {c.strip().lower() for c in category.split(",")}
        invalid = cat_filter - VALID_CATEGORIES
        if invalid:
            console.print(
                f"[red]Invalid category: {', '.join(sorted(invalid))}[/red]"
            )
            console.print(
                f"[dim]Valid categories: {', '.join(sorted(VALID_CATEGORIES))}[/dim]"
            )
            raise typer.Exit(1)

    assistant_id = settings.project_assistant_id
    if not assistant_id and not search_all:
        console.print("[red]No project assistant configured.[/red]")
        console.print("Run [bold]tribal init[/bold] first.")
        raise typer.Exit(1)

    # List mode: no search, no RAG cost
    if list_all:
        try:
            results = asyncio.run(_list_all(assistant_id))
        except BackboardError as e:
            console.print(f"[red]API error {e.status_code}:[/red] {e.detail}")
            raise typer.Exit(1)

        if cat_filter:
            results = _filter_by_category(results, cat_filter)

        if json_output:
            output = {
                "count": len(results),
                "results": [_memory_to_dict(r) for r in results],
            }
            typer.echo(json.dumps(output, indent=2))
            return

        if not results:
            console.print("[dim]No memories stored yet.[/dim]")
            return

        table = _make_table("All Memories")
        for r in results:
            _add_row(table, r)

        console.print(table)
        console.print(f"[dim]{len(results)} memor{'y' if len(results) == 1 else 'ies'}[/dim]")
        return

    # Search mode: requires a query
    if query:
        query_text = " ".join(query)
    elif not sys.stdin.isatty():
        query_text = sys.stdin.read().strip()
    else:
        console.print(
            "[yellow]No query provided.[/yellow]"
            " Pass a search query or use --list to browse all."
        )
        raise typer.Exit(1)

    if not query_text:
        console.print("[yellow]Empty query.[/yellow]")
        raise typer.Exit(1)

    # Cross-repo search: query every assistant in the account
    if search_all:
        try:
            if not json_output:
                with console.status("[bold #a78bfa]Searching all repos...[/bold #a78bfa]"):
                    grouped = asyncio.run(_search_all_assistants(query_text, limit))
            else:
                grouped = asyncio.run(_search_all_assistants(query_text, limit))
        except BackboardError as e:
            console.print(f"[red]API error {e.status_code}:[/red] {e.detail}")
            raise typer.Exit(1)

        if cat_filter:
            grouped = [
                (name, _filter_by_category(results, cat_filter))
                for name, results in grouped
            ]
            grouped = [(name, results) for name, results in grouped if results]

        total = sum(len(results) for _, results in grouped)

        from tribalmind.activity import log_activity
        log_activity(
            "recall",
            f"searched all repos: {query_text}",
            query=query_text,
            count=total,
            metadata={"scope": "all", "repos": len(grouped)},
        )

        if json_output:
            output = {
                "query": query_text,
                "scope": "all",
                "repos": [
                    {
                        "assistant": name,
                        "count": len(results),
                        "results": [_memory_to_search_dict(r) for r in results],
                    }
                    for name, results in grouped
                ],
            }
            typer.echo(json.dumps(output, indent=2))
            return

        if not grouped:
            console.print("[dim]No memories found across any repo.[/dim]")
            return

        for name, results in grouped:
            display_name = name

            table = _make_table(
                f"[#a78bfa]{display_name}[/] — {len(results)} result(s)",
                show_relevance=True,
            )
            for r in results:
                _add_row(table, r, show_relevance=True)

            console.print(table)
            console.print()

        console.print(f"[dim]{total} result(s) across {len(grouped)} repo(s)[/dim]")
        return

    # Single-repo search
    try:
        results = asyncio.run(_search(assistant_id, query_text, limit))
    except BackboardError as e:
        console.print(f"[red]API error {e.status_code}:[/red] {e.detail}")
        raise typer.Exit(1)

    if cat_filter:
        results = _filter_by_category(results, cat_filter)

    from tribalmind.activity import log_activity
    log_activity(
        "recall",
        f"searched: {query_text}",
        query=query_text,
        count=len(results),
    )

    if json_output:
        output = {
            "query": query_text,
            "count": len(results),
            "results": [_memory_to_search_dict(r) for r in results],
        }
        typer.echo(json.dumps(output, indent=2))
        return

    if not results:
        console.print("[dim]No memories found.[/dim]")
        return

    table = _make_table(f"Memories matching: {query_text}", show_relevance=True)
    for r in results:
        _add_row(table, r, show_relevance=True)

    console.print(table)
    console.print(f"[dim]{len(results)} result(s)[/dim]")
