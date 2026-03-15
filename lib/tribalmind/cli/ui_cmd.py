"""CLI command for launching the TribalMind dashboard UI."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import typer
from rich.console import Console

console = Console()

UI_PORT = 7484

_STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"
_UI_SRC_DIR = Path(__file__).resolve().parent.parent.parent.parent / "ui"


def _build_frontend() -> bool:
    """Try to build the React frontend. Returns True on success."""
    if not _UI_SRC_DIR.exists():
        return False

    # On Windows, node package managers are .cmd scripts that require shell=True
    use_shell = sys.platform == "win32"

    for pkg_manager in ("pnpm", "npm"):
        try:
            subprocess.run(
                [pkg_manager, "--version"],
                capture_output=True,
                shell=use_shell,
                check=True,
            )
            break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    else:
        return False

    console.print(f"[yellow]Building frontend with {pkg_manager}…[/yellow]")
    try:
        subprocess.run(
            [pkg_manager, "install"],
            cwd=str(_UI_SRC_DIR),
            check=True,
            capture_output=True,
            shell=use_shell,
        )
        subprocess.run(
            [pkg_manager, "run", "build"],
            cwd=str(_UI_SRC_DIR),
            check=True,
            capture_output=True,
            shell=use_shell,
        )
        console.print("[green]Frontend built successfully.[/green]")
        return True
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.decode() if exc.stderr else ""
        console.print(f"[red]Frontend build failed:[/red] {stderr[:500]}")
        return False


def ui(
    port: int = typer.Option(UI_PORT, "--port", "-p", help="Port for the web UI server."),
    no_browser: bool = typer.Option(
        False, "--no-browser", help="Don't open a browser automatically."
    ),
) -> None:
    """Launch the TribalMind dashboard in your browser.

    Browse assistants, memories, and threads via a web interface backed
    by the Backboard API.
    """
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        console.print("[red]Web UI requires extra dependencies:[/red]")
        console.print("  pip install 'tribalmind[ui]'")
        raise typer.Exit(1)

    if not _STATIC_DIR.exists():
        if not _build_frontend():
            console.print("[red]Frontend assets not found.[/red]")
            console.print("Build manually: [cyan]cd ui && pnpm install && pnpm build[/cyan]")
            raise typer.Exit(1)

    import threading
    import webbrowser

    url = f"http://localhost:{port}"
    console.print(f"[green]TribalMind dashboard ->[/green] {url}")
    console.print("[dim]Press Ctrl+C to stop.[/dim]")

    if not no_browser:
        def _open_browser() -> None:
            import time
            time.sleep(0.8)
            webbrowser.open(url)

        threading.Thread(target=_open_browser, daemon=True).start()

    import uvicorn

    from tribalmind.web.server import app

    uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")
