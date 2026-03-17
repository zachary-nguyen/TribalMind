"""CLI commands for managing shell completions."""

from __future__ import annotations

import shutil
import subprocess
import sys

import typer
from rich.console import Console

completion_app = typer.Typer(no_args_is_help=True)
console = Console()

SUPPORTED_SHELLS = ("bash", "zsh", "fish", "powershell")

_INSTALL_HINTS: dict[str, str] = {
    "bash": (
        'Add to your [bold]~/.bashrc[/bold]:\n\n'
        '  eval "$(tribal --show-completion bash)"\n\n'
        'Then reload: [dim]source ~/.bashrc[/dim]'
    ),
    "zsh": (
        'Add to your [bold]~/.zshrc[/bold]:\n\n'
        '  eval "$(tribal --show-completion zsh)"\n\n'
        'Then reload: [dim]source ~/.zshrc[/dim]'
    ),
    "fish": (
        'Save the completion script:\n\n'
        '  tribal --show-completion fish > ~/.config/fish/completions/tribal.fish\n\n'
        'Completions are loaded automatically on next shell start.'
    ),
    "powershell": (
        'Add to your [bold]PowerShell profile[/bold] ($PROFILE):\n\n'
        '  tribal --show-completion powershell | Out-String | Invoke-Expression\n\n'
        'Then restart PowerShell.'
    ),
}


def _resolve_tribal() -> list[str]:
    """Return the command list to invoke the tribal CLI."""
    tribal = shutil.which("tribal")
    if tribal:
        return [tribal]
    # Fall back to running the module directly
    return [sys.executable, "-m", "tribalmind.cli.app"]


def _validate_shell(shell: str) -> str:
    shell = shell.lower()
    if shell not in SUPPORTED_SHELLS:
        console.print(
            f"[red]Unsupported shell:[/red] {shell}. "
            f"Supported: {', '.join(SUPPORTED_SHELLS)}."
        )
        raise typer.Exit(1)
    return shell


@completion_app.command("show")
def show(
    shell: str = typer.Argument(
        ...,
        help="Shell to generate completions for (bash, zsh, fish, powershell).",
    ),
) -> None:
    """Print the completion script for a given shell.

    Outputs the shell completion script to stdout so you can save or eval it.
    """
    shell = _validate_shell(shell)

    result = subprocess.run(
        [*_resolve_tribal(), "--show-completion", shell],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0 and result.stdout.strip():
        typer.echo(result.stdout)
    else:
        console.print(
            f"[yellow]Could not generate completion script automatically.[/yellow]\n"
            f"Try running: [bold]tribal --show-completion {shell}[/bold]"
        )
        raise typer.Exit(1)


@completion_app.command("install")
def install(
    shell: str = typer.Argument(
        ...,
        help="Shell to install completions for (bash, zsh, fish, powershell).",
    ),
) -> None:
    """Install completions for a given shell (uses Typer's built-in installer).

    This is a shortcut for `tribal --install-completion <shell>`.
    """
    shell = _validate_shell(shell)

    result = subprocess.run(
        [*_resolve_tribal(), "--install-completion", shell],
        capture_output=True,
        text=True,
    )
    if result.returncode == 0:
        console.print(f"[green]Completions installed for {shell}.[/green]")
        if result.stdout.strip():
            console.print(result.stdout.strip())
    else:
        console.print(
            f"[yellow]Automatic installation not available for {shell}.[/yellow]\n"
        )
        console.print(_INSTALL_HINTS[shell])


@completion_app.command("instructions")
def instructions(
    shell: str = typer.Argument(
        None,
        help="Shell to show instructions for. Omit to see all shells.",
    ),
) -> None:
    """Show manual installation instructions for shell completions."""
    if shell is not None:
        shell = _validate_shell(shell)
        shells = [shell]
    else:
        shells = list(SUPPORTED_SHELLS)

    console.print("[bold]Shell Completion Instructions[/bold]\n")
    for name in shells:
        console.print(f"[bold #818cf8]{name}[/bold #818cf8]")
        console.print(_INSTALL_HINTS[name])
        console.print()
