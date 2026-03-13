"""CLI commands for managing TribalMind configuration."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from tribalmind.config.credentials import (
    BACKBOARD_API_KEY,
    GITHUB_TOKEN,
    set_credential,
)
from tribalmind.config.settings import TribalSettings, clear_settings_cache

config_app = typer.Typer(no_args_is_help=True)
console = Console()

SECRET_KEYS = {
    "backboard-api-key": BACKBOARD_API_KEY,
    "github-token": GITHUB_TOKEN,
}

# Settings fields that can be modified via `tribal config set`
CONFIGURABLE_KEYS = {
    "backboard-base-url": "backboard_base_url",
    "llm-provider": "llm_provider",
    "model-name": "model_name",
    "embedding-provider": "embedding_provider",
    "embedding-model": "embedding_model",
    "daemon-host": "daemon_host",
    "daemon-port": "daemon_port",
    "team-sharing-enabled": "team_sharing_enabled",
    "org-assistant-id": "org_assistant_id",
    "project-assistant-id": "project_assistant_id",
}

REDACTED_FIELDS = {"backboard_api_key", "github_token"}


def _get_config_path() -> Path:
    """Get the tribal.yaml path in the current directory."""
    return Path.cwd() / "tribal.yaml"


def _load_config_file(path: Path) -> dict:
    if path.exists():
        with open(path) as f:
            data = yaml.safe_load(f)
        return data if isinstance(data, dict) else {}
    return {}


def _save_config_file(path: Path, data: dict) -> None:
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(help="Configuration key (e.g., llm-provider, model-name)"),
    value: str = typer.Argument(help="Value to set"),
) -> None:
    """Set a configuration value in tribal.yaml."""
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
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")

    for field_name, field_info in settings.model_fields.items():
        value = getattr(settings, field_name)
        display_value = "****" if field_name in REDACTED_FIELDS and value else str(value)
        table.add_row(field_name, display_value)

    console.print(table)


@config_app.command("set-secret")
def config_set_secret(
    name: str = typer.Argument(help="Secret name: backboard-api-key or github-token"),
) -> None:
    """Store a secret in the system keyring."""
    if name not in SECRET_KEYS:
        valid = ", ".join(sorted(SECRET_KEYS.keys()))
        console.print(f"[red]Unknown secret:[/red] {name}")
        console.print(f"Valid secrets: {valid}")
        raise typer.Exit(1)

    value = typer.prompt(f"Enter value for {name}", hide_input=True)
    if not value:
        console.print("[red]Value cannot be empty.[/red]")
        raise typer.Exit(1)

    credential_key = SECRET_KEYS[name]
    set_credential(credential_key, value)
    clear_settings_cache()
    console.print(f"[green]Stored[/green] {name} in system keyring.")
