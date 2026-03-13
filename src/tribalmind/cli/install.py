"""CLI command for installing TribalMind shell hooks and initial setup."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()


def install(
    shell: str | None = typer.Option(None, "--shell", "-s", help="Shell to install hook for (bash, zsh, powershell). Auto-detected if omitted."),
    skip_hooks: bool = typer.Option(False, "--skip-hooks", help="Skip shell hook installation."),
) -> None:
    """Install TribalMind: set up shell hooks and configure credentials."""
    from tribalmind.config.credentials import get_backboard_api_key, set_credential, BACKBOARD_API_KEY
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
            console.print("[yellow]Skipping API key setup. Set it later with: tribal config set-secret backboard-api-key[/yellow]")

    # Step 2: Install shell hooks
    if not skip_hooks:
        target_shell = shell or detect_shell()
        if target_shell:
            console.print(f"\nDetected shell: [cyan]{target_shell}[/cyan]")
            install_hook(target_shell)
            console.print(f"[green]Shell hook installed for {target_shell}.[/green]")
            console.print("Restart your shell or source the config file to activate.")
        else:
            console.print("[yellow]Could not detect shell. Use --shell to specify manually.[/yellow]")
    else:
        console.print("Skipped shell hook installation.")

    console.print("\n[bold green]Installation complete![/bold green]")
    console.print("Start the daemon with: [cyan]tribal start[/cyan]")
