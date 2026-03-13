"""CLI command for enabling team sharing."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def enable_team_sharing(
    org_assistant_id: str = typer.Option(
        ..., "--org-id", prompt="Enter your organization's Backboard assistant ID",
        help="The Backboard assistant ID for your organization's shared knowledge base.",
    ),
) -> None:
    """Enable team-wide knowledge sharing via Backboard.

    This connects your local TribalMind instance to a shared organization
    knowledge base. Validated fixes that reach the trust threshold will be
    promoted to the shared assistant, and team knowledge will be included
    in context searches.
    """
    from tribalmind.cli.config_cmd import _get_config_path, _load_config_file, _save_config_file
    from tribalmind.config.settings import clear_settings_cache

    config_path = _get_config_path()
    data = _load_config_file(config_path)
    data["team_sharing_enabled"] = True
    data["org_assistant_id"] = org_assistant_id
    _save_config_file(config_path, data)
    clear_settings_cache()

    console.print(f"[green]Team sharing enabled.[/green]")
    console.print(f"Organization assistant ID: [cyan]{org_assistant_id}[/cyan]")
    console.print("Validated fixes will now be shared with your team.")
