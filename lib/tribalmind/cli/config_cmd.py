"""CLI commands for managing TribalMind configuration."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from tribalmind.config.credentials import (
    BACKBOARD_API_KEY,
    get_credential,
    set_credential,
)
from tribalmind.config.settings import TribalSettings, clear_settings_cache

config_app = typer.Typer(no_args_is_help=True)
console = Console()

SECRET_KEYS = {
    "backboard-api-key": BACKBOARD_API_KEY,
}

# Settings fields that can be modified via `tribal config set`
CONFIGURABLE_KEYS = {
    "backboard-base-url": "backboard_base_url",
    "llm-provider": "llm_provider",
    "model-name": "model_name",
    "project-assistant-id": "project_assistant_id",
}

REDACTED_FIELDS = {"backboard_api_key"}


def _get_config_path() -> Path:
    """Get the project config path in the current directory (.tribal/config.yaml)."""
    return Path.cwd() / ".tribal" / "config.yaml"


def _load_config_file(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    return {}


def _save_config_file(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Configuration key (e.g., llm-provider, model-name)"),
    value: str = typer.Argument(help="Value to set"),
) -> None:
    """Set a configuration value in .tribal/config.yaml."""
    if key not in CONFIGURABLE_KEYS:
        valid = ", ".join(sorted(CONFIGURABLE_KEYS.keys()))
        console.print(f"[red]Unknown key:[/red] {key}")
        console.print(f"Valid keys: {valid}")
        raise typer.Exit(1)

    config_path = _get_config_path()
    data = _load_config_file(config_path)
    field_name = CONFIGURABLE_KEYS[key]
    data[field_name] = value
    _save_config_file(config_path, data)
    clear_settings_cache()
    console.print(f"[green]Set[/green] {key} = {value} in {config_path}")


@config_app.command("get")
def config_get(
    key: str = typer.Argument(help="Configuration key to read"),
) -> None:
    """Get a resolved configuration value."""
    if key not in CONFIGURABLE_KEYS:
        valid = ", ".join(sorted(CONFIGURABLE_KEYS.keys()))
        console.print(f"[red]Unknown key:[/red] {key}")
        console.print(f"Valid keys: {valid}")
        raise typer.Exit(1)

    settings = TribalSettings()
    field_name = CONFIGURABLE_KEYS[key]
    value = getattr(settings, field_name, None)
    console.print(f"{key} = {value}")


@config_app.command("list")
def config_list() -> None:
    """Show all resolved configuration values."""
    settings = TribalSettings()
    table = Table(title="TribalMind Configuration", show_lines=True)
    table.add_column("Key", style="#a78bfa")
    table.add_column("Value", style="#34d399")

    for field_name, field_info in settings.model_fields.items():
        value = getattr(settings, field_name)
        display_value = "****" if field_name in REDACTED_FIELDS and value else str(value)
        table.add_row(field_name, display_value)

    console.print(table)


@config_app.command("set-secret")
def config_set_secret(
    name: str = typer.Argument(help="Secret name: backboard-api-key or github-token"),
    value: str | None = typer.Option(
        None, "--value", "-v",
        help="Secret value (if omitted, you'll be prompted).",
    ),
) -> None:
    """Store a secret in the system keyring."""
    if name not in SECRET_KEYS:
        valid = ", ".join(sorted(SECRET_KEYS.keys()))
        console.print(f"[red]Unknown secret:[/red] {name}")
        console.print(f"Valid secrets: {valid}")
        raise typer.Exit(1)

    if not value:
        value = typer.prompt(f"Enter value for {name}", hide_input=True)
    if not value or len(value) < 8:
        console.print(
            "[red]Value is empty or too short (< 8 chars).[/red] "
            "If paste isn't working, use: "
            f"[#a78bfa]tribal config set-secret {name} --value YOUR_KEY[/#a78bfa]"
        )
        raise typer.Exit(1)

    credential_key = SECRET_KEYS[name]
    stored_in_keyring = set_credential(credential_key, value)
    if not stored_in_keyring:
        config_path = _get_config_path()
        data = _load_config_file(config_path)
        data[credential_key] = value.strip()
        _save_config_file(config_path, data)
    clear_settings_cache()
    masked = value[:4] + "\u2022" * 8 + value[-4:]
    location = "system keyring" if stored_in_keyring else "config file"
    console.print(f"[green]Stored[/green] {name} in {location}: {masked}")


@config_app.command("assistants")
def config_assistants() -> None:
    """List all Backboard assistants (debug helper)."""
    import asyncio

    from tribalmind.backboard.assistants import list_assistants
    from tribalmind.backboard.client import BackboardError, create_client

    async def _list():
        async with create_client() as client:
            return await list_assistants(client)

    try:
        assistants = asyncio.run(_list())
    except BackboardError as e:
        console.print(f"[red]API error {e.status_code}:[/red] {e.detail}")
        raise typer.Exit(1)

    if not assistants:
        console.print("[dim]No assistants found.[/dim]")
        return

    table = Table(title="Backboard Assistants")
    table.add_column("ID", style="#a78bfa")
    table.add_column("Name", style="#34d399")
    table.add_column("Created", style="dim")

    for a in assistants:
        table.add_row(
            a.get("assistant_id", "?"),
            a.get("name", "?"),
            a.get("created_at", "?"),
        )

    console.print(table)


@config_app.command("clear-memory")
def config_clear_memory(
    assistant_id: str | None = typer.Option(
        None, "--assistant", "-a",
        help="Assistant ID (defaults to project assistant).",
    ),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation prompt."),
) -> None:
    """Clear ALL memories for an assistant."""
    import asyncio

    from tribalmind.backboard.client import BackboardError, create_client
    from tribalmind.backboard.memory import clear_memories

    settings = TribalSettings()
    target_id = assistant_id or settings.project_assistant_id

    if not target_id:
        console.print(
            "[red]No assistant ID specified.[/red] "
            "Use --assistant or set project-assistant-id in .tribal/config.yaml."
        )
        raise typer.Exit(1)

    if not yes:
        confirm = typer.confirm(f"Delete ALL memories for assistant {target_id}?")
        if not confirm:
            raise typer.Abort()

    async def _clear():
        async with create_client() as client:
            return await clear_memories(client, target_id)

    try:
        deleted = asyncio.run(_clear())
        console.print(f"[green]Cleared[/green] {deleted} memories from assistant {target_id}")
    except BackboardError as e:
        console.print(f"[red]API error {e.status_code}:[/red] {e.detail}")
        raise typer.Exit(1)


@config_app.command("debug-key")
def config_debug_key() -> None:
    """Show API key details for debugging connection issues."""
    raw = get_credential(BACKBOARD_API_KEY)
    if not raw:
        console.print("[red]No API key in keyring.[/red]")
        return

    console.print(f"Length:  {len(raw)} chars")
    if len(raw) >= 8:
        console.print(f"Key:    {raw[:6]}{'•' * 12}{raw[-6:]}")
        console.print("[green]Key looks valid.[/green]")
    else:
        console.print(f"[red]Key is too short ({len(raw)} chars) — likely corrupted.[/red]")
        console.print(
            "Re-set with: [#a78bfa]tribal config set-secret"
            " backboard-api-key --value YOUR_KEY[/#a78bfa]"
        )
