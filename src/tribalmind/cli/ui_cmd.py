"""CLI command for launching the TribalMind live log viewer UI."""

from __future__ import annotations

import typer
from rich.console import Console

console = Console()

UI_PORT = 7484


def ui(
    port: int = typer.Option(UI_PORT, "--port", "-p", help="Port for the web UI server."),
    no_browser: bool = typer.Option(False, "--no-browser", help="Don't open a browser automatically."),
) -> None:
    """Launch the live log viewer UI in your browser."""
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        console.print("[red]Web UI requires extra dependencies:[/red]")
        console.print("  pip install 'tribalmind[[ui]]'")
        raise typer.Exit(1)

    import threading
    import webbrowser

    url = f"http://localhost:{port}"
    console.print(f"[green]TribalMind UI →[/green] {url}")
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
