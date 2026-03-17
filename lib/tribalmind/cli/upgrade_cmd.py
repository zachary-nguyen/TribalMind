"""Upgrade command - install latest TribalMind from PyPI."""

from __future__ import annotations

import subprocess
import sys

import typer
from rich.console import Console

console = Console()

_CHECK = "[bold #34d399]\u2714[/bold #34d399]"


def _update_agent_docs() -> list[tuple[str, str]]:
    """Detect and update TribalMind instruction blocks in agent config files.

    Scans the current project for known agent config files (CLAUDE.md,
    AGENTS.md, etc.) and replaces the TribalMind section with the latest
    template.

    Returns a list of (file_path, result) tuples where result is one of
    'created', 'updated', or 'unchanged'.
    """
    from tribalmind.cli.agents_cmd import (
        AGENT_SNIPPETS,
        AGENTS,
        _detect_agents,
        _find_project_root,
        _inject_snippet,
    )

    root = _find_project_root()
    detected = _detect_agents(root)

    if not detected:
        return []

    results = []
    for key in detected:
        info = AGENTS[key]
        file_path = root / info["path"]
        snippet = AGENT_SNIPPETS[info["snippet_key"]]
        result = _inject_snippet(file_path, snippet, info["section_marker"])
        results.append((info["path"], result))

    return results


def upgrade(
    no_update_docs: bool = typer.Option(
        False,
        "--no-update-docs",
        help="Skip auto-updating agent config files (CLAUDE.md, AGENTS.md, etc.).",
    ),
) -> None:
    """Upgrade TribalMind to the latest version from PyPI.

    After upgrading the package, automatically updates any agent config files
    (CLAUDE.md, AGENTS.md, etc.) to match the latest TribalMind instruction
    template.  Use --no-update-docs to skip this step.
    """
    console.print("Upgrading TribalMind...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "tribalmind"],
        capture_output=False,
    )
    if result.returncode != 0:
        raise typer.Exit(result.returncode)

    if no_update_docs:
        console.print("\n[dim]Skipped agent doc updates (--no-update-docs).[/dim]")
        return

    # Auto-update agent config files
    console.print("\n[bold]Updating agent config files...[/bold]")
    doc_results = _update_agent_docs()

    if not doc_results:
        console.print("  [dim]No agent config files detected in this project.[/dim]")
        return

    any_updated = False
    for path, status in doc_results:
        if status == "updated":
            console.print(f"  {_CHECK} [yellow]updated[/yellow]  {path}")
            any_updated = True
        elif status == "unchanged":
            console.print(f"  {_CHECK} [dim]unchanged[/dim]  {path}")

    if any_updated:
        console.print(
            "\n[dim]Tip: review the updated files and commit them to your repo.[/dim]"
        )
