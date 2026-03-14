"""CLI commands for managing watched directories."""

from __future__ import annotations

from pathlib import Path

import typer
import yaml
from rich.console import Console
from rich.table import Table

from tribalmind.config.settings import clear_settings_cache, get_settings

watch_app = typer.Typer(no_args_is_help=True)
console = Console()


def _user_config_path() -> Path:
    """User-level tribal.yaml (applies across all projects)."""
    settings = get_settings()
    return settings.config_dir / "tribal.yaml"


def _load(path: Path) -> dict:
    if path.exists():
        data = yaml.safe_load(path.read_text())
        return data if isinstance(data, dict) else {}
    return {}


def _save(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)


@watch_app.command("add")
def watch_add(
    path: Path = typer.Argument(
        default=None,
        help="Directory to watch. Defaults to the current directory.",
    ),
) -> None:
    """Add a directory to the watch list."""
    target = (path or Path.cwd()).resolve()

    if not target.is_dir():
        console.print(f"[red]Not a directory:[/red] {target}")
        raise typer.Exit(1)

    config_path = _user_config_path()
    data = _load(config_path)
    dirs: list[str] = data.get("watch_dirs", [])

    if str(target) in dirs:
        console.print(f"[yellow]Already watching:[/yellow] {target}")
        raise typer.Exit(0)

    dirs.append(str(target))
    data["watch_dirs"] = dirs
    _save(config_path, data)
    clear_settings_cache()

    console.print(f"[green]Watching:[/green] {target}")
    console.print("[dim]Restart the daemon for changes to take effect: "
                  "tribal stop && tribal start[/dim]")


@watch_app.command("remove")
def watch_remove(
    path: Path = typer.Argument(
        default=None,
        help="Directory to stop watching. Defaults to the current directory.",
    ),
) -> None:
    """Remove a directory from the watch list."""
    target = (path or Path.cwd()).resolve()

    config_path = _user_config_path()
    data = _load(config_path)
    dirs: list[str] = data.get("watch_dirs", [])

    if str(target) not in dirs:
        console.print(f"[yellow]Not in watch list:[/yellow] {target}")
        raise typer.Exit(0)

    dirs.remove(str(target))
    data["watch_dirs"] = dirs
    _save(config_path, data)
    clear_settings_cache()

    console.print(f"[red]Removed:[/red] {target}")
    console.print("[dim]Restart the daemon for changes to take effect: "
                  "tribal stop && tribal start[/dim]")


@watch_app.command("list")
def watch_list() -> None:
    """Show all watched directories."""
    settings = get_settings()

    if not settings.watch_dirs:
        console.print(
            "[yellow]No directories configured — daemon is not monitoring any commands.[/yellow]"
        )
        console.print("[dim]Add one with: tribal watch add [path][/dim]")
        return

    table = Table(title="Watched Directories", show_lines=True)
    table.add_column("#", style="dim", width=4)
    table.add_column("Path", style="cyan")
    table.add_column("Exists", width=8)

    for i, d in enumerate(settings.watch_dirs, 1):
        exists = "[green]yes[/green]" if d.is_dir() else "[red]no[/red]"
        table.add_row(str(i), str(d), exists)

    console.print(table)
