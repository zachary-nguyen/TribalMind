"""CLI command for installing TribalMind shell hooks and initial setup."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()


def install(
    shell: str | None = typer.Option(
        None, "--shell", "-s",
        help="Shell to install hook for (bash, zsh, powershell). Auto-detected if omitted.",
    ),
    skip_hooks: bool = typer.Option(False, "--skip-hooks", help="Skip shell hook installation."),
) -> None:
    """Install TribalMind: set up shell hooks and configure credentials."""
    from tribalmind.config.credentials import (
        BACKBOARD_API_KEY,
        get_backboard_api_key,
        set_credential,
    )
    from tribalmind.hooks.generator import detect_shell, install_hook

    console.print("[bold]TribalMind Installation[/bold]\n")

    # Step 1: Check / prompt for Backboard API key
    api_key = get_backboard_api_key()
    if not api_key:
        console.print("No Backboard API key found.")
        api_key = typer.prompt("Enter your Backboard API key", hide_input=True)
        if api_key:
            set_credential(BACKBOARD_API_KEY, api_key)
            console.print("[green]API key stored in system keyring.[/green]")
        else:
            console.print(
                "[yellow]Skipping API key setup. "
                "Set it later with: tribal config set-secret backboard-api-key[/yellow]"
            )

    # Step 2: Install shell hooks
    if not skip_hooks:
        target_shell = shell or detect_shell()
        if target_shell:
            console.print(f"\nDetected shell: [cyan]{target_shell}[/cyan]")
            install_hook(target_shell)
            console.print(f"[green]Shell hook installed for {target_shell}.[/green]")
            console.print("Restart your shell or source the config file to activate.")
        else:
            console.print(
                "[yellow]Could not detect shell. Use --shell to specify manually.[/yellow]"
            )
    else:
        console.print("Skipped shell hook installation.")

    # Step 3: Configure watched directories
    _setup_watch_dirs()

    console.print("\n[bold green]Installation complete![/bold green]")
    console.print("Start the daemon with: [cyan]tribal start[/cyan]")


def _setup_watch_dirs() -> None:
    """Interactively prompt the user to configure watched directories."""
    import yaml

    from tribalmind.config.settings import clear_settings_cache, get_settings

    console.print("\n[bold]Watched Directories[/bold]")
    console.print("TribalMind only monitors commands run inside directories you specify.")
    console.print("[dim]Press Enter with no input to finish.[/dim]\n")

    settings = get_settings()
    config_path = settings.config_dir / "tribal.yaml"
    existing: list[str] = [str(d) for d in settings.watch_dirs]

    if existing:
        console.print("Currently watching:")
        for d in existing:
            console.print(f"  [cyan]{d}[/cyan]")
        if not typer.confirm("\nAdd more directories?", default=False):
            return

    dirs = list(existing)
    while True:
        raw = typer.prompt(
            "Directory to watch (Enter to skip)",
            default="",
            show_default=False,
        )
        if not raw:
            break

        target = Path(raw).expanduser().resolve()
        if not target.is_dir():
            console.print(f"[red]Not a directory:[/red] {target}")
            continue
        if str(target) in dirs:
            console.print(f"[yellow]Already added:[/yellow] {target}")
            continue

        dirs.append(str(target))
        console.print(f"[green]Added:[/green] {target}")

    if not dirs:
        console.print("[yellow]No directories set. Add them later with: tribal watch add[/yellow]")
        return

    # Persist to user config
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data: dict = {}
    if config_path.exists():
        loaded = yaml.safe_load(config_path.read_text())
        data = loaded if isinstance(loaded, dict) else {}

    data["watch_dirs"] = dirs
    with open(config_path, "w") as f:
        yaml.dump(data, f, default_flow_style=False, sort_keys=False)

    clear_settings_cache()
    noun = "directory" if len(dirs) == 1 else "directories"
    console.print(f"\n[green]Watching {len(dirs)} {noun}.[/green]")
