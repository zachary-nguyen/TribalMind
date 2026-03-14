"""CLI command for installing TribalMind shell hooks and initial setup."""

from __future__ import annotations

import logging

import typer
from rich.console import Console
from rich.panel import Panel

console = Console()
logger = logging.getLogger(__name__)


def install(
    shell: str | None = typer.Option(
        None, "--shell", "-s",
        help="Shell(s) to install hooks for, comma-separated (e.g. powershell,cmd). "
             "Interactive selection if omitted.",
    ),
    skip_hooks: bool = typer.Option(False, "--skip-hooks", help="Skip shell hook installation."),
    verbose: bool = typer.Option(False, "--verbose", "-V", help="Enable debug logging."),
) -> None:
    """Install TribalMind: set up shell hooks and configure credentials."""
    from tribalmind.cli.banner import print_banner

    if verbose:
        logging.basicConfig(level=logging.DEBUG, format="%(name)s: %(message)s")
    else:
        logging.basicConfig(level=logging.WARNING)

    print_banner()
    console.print()

    # ── Step 1: Backboard API key ──────────────────────────────────────
    api_key = _setup_api_key()

    # ── Step 2: Project assistant ──────────────────────────────────────
    if api_key:
        _setup_project_assistant()

    # ── Step 3: Shell hooks ────────────────────────────────────────────
    if not skip_hooks:
        _setup_shell_hooks(shell)

    # ── Step 4: Watch directories ──────────────────────────────────────
    _setup_watch_dirs()

    # ── Done ───────────────────────────────────────────────────────────
    console.print()
    console.print(Panel(
        "[bold green]Setup complete![/bold green]\n\n"
        "Start the daemon:  [cyan]tribal daemon start[/cyan]\n"
        "View live logs:    [cyan]tribal daemon logs[/cyan]\n"
        "Open the web UI:   [cyan]tribal ui[/cyan]",
        border_style="green",
        padding=(1, 2),
    ))


def _step(number: int, title: str) -> None:
    """Print a styled step header."""
    console.print(f"[bold white]  {number}. {title}[/bold white]")


def _ok(msg: str) -> None:
    console.print(f"     [green]\u2714[/green] {msg}")


def _warn(msg: str) -> None:
    console.print(f"     [yellow]\u26a0[/yellow] {msg}")


def _info(msg: str) -> None:
    console.print(f"     [dim]{msg}[/dim]")


# ── Step implementations ───────────────────────────────────────────────


def _setup_api_key() -> str | None:
    """Check or prompt for the Backboard API key."""
    from tribalmind.config.credentials import (
        BACKBOARD_API_KEY,
        get_backboard_api_key,
        set_credential,
    )

    _step(1, "Backboard API Key")

    api_key = get_backboard_api_key()
    if api_key:
        masked = api_key[:4] + "\u2022" * 12 + api_key[-4:]
        _ok(f"Found in keyring: {masked}")
        return api_key

    _info("Get your API key at https://app.backboard.io/settings")
    api_key = typer.prompt("     Enter your Backboard API key", hide_input=True)
    if api_key:
        set_credential(BACKBOARD_API_KEY, api_key)
        _ok("Saved to system keyring")
        return api_key

    _warn("Skipped. Set later with: tribal config set-secret backboard-api-key")
    return None


def _setup_project_assistant() -> None:
    """Create or find the Backboard assistant for the current project."""
    import asyncio

    import yaml

    from tribalmind.backboard.assistants import get_or_create_project_assistant
    from tribalmind.backboard.client import BackboardError, create_client
    from tribalmind.config.settings import clear_settings_cache, get_settings

    _step(2, "Project Assistant")

    settings = get_settings()

    if settings.project_assistant_id:
        _ok(f"Already configured: {settings.project_assistant_id}")
        return

    project_root = str(settings.project_root)
    _info(f"Project: {project_root}")

    try:
        async def _create():
            async with create_client() as client:
                return await get_or_create_project_assistant(client, project_root)

        assistant = asyncio.run(_create())
        assistant_id = assistant.get("assistant_id", "")

        if not assistant_id:
            logger.error("Unexpected API response (no id field): %s", assistant)
            _warn("Unexpected API response — no assistant ID returned")
            return

        # Persist to user config
        config_path = settings.config_dir / "tribal.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data: dict = {}
        if config_path.exists():
            loaded = yaml.safe_load(config_path.read_text())
            data = loaded if isinstance(loaded, dict) else {}

        data["project_assistant_id"] = assistant_id
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)

        clear_settings_cache()
        _ok(f"Ready: {assistant_id}")

    except BackboardError as e:
        logger.error(
            "Backboard API error creating assistant: %s (status %s)",
            e.detail, e.status_code,
        )
        _warn(f"API error {e.status_code}: {e.detail}")
        _info("Set manually with: tribal config set project_assistant_id <id>")
    except Exception as e:
        logger.error("Failed to create project assistant: %s", e, exc_info=True)
        _warn(f"Failed: {e}")
        _info("Set manually with: tribal config set project_assistant_id <id>")


def _setup_shell_hooks(shell_arg: str | None) -> None:
    """Detect available shells and let the user choose which to monitor."""
    from tribalmind.hooks.generator import install_hook, list_available_shells

    _step(3, "Shell Hooks")

    # If --shell flag provided, install those directly
    if shell_arg:
        targets = [s.strip().lower() for s in shell_arg.split(",")]
        for target in targets:
            try:
                install_hook(target)
                _ok(f"Installed for {target}")
            except Exception as e:
                _warn(f"Failed to install {target} hook: {e}")
        _info("Restart your shells to activate")
        return

    # Discover available shells
    shells = list_available_shells()
    available = [s for s in shells if s["available"]]

    if not available:
        _warn("No supported shells detected.")
        return

    not_installed = [s for s in available if not s["installed"]]
    if not not_installed:
        _ok("All available shells already have hooks installed")
        return

    # Interactive picker
    _info("Select which shells to monitor:")
    console.print()

    from tribalmind.cli.shell_picker import pick_shells

    selected = pick_shells(available)

    if not selected:
        _warn("No new shells selected")
        return

    for target in selected:
        try:
            install_hook(target)
            label = next(s["label"] for s in available if s["name"] == target)
            _ok(f"Installed for {label}")
        except Exception as e:
            _warn(f"Failed to install {target} hook: {e}")

    _info("Restart your shells to activate")


def _setup_watch_dirs() -> None:
    """Interactively prompt the user to configure watched directories."""
    import yaml

    from tribalmind.cli.dir_picker import pick_directory
    from tribalmind.config.settings import clear_settings_cache, get_settings

    _step(4, "Watch Directories")
    _info("Only monitor commands in directories you choose")
    console.print()

    settings = get_settings()
    config_path = settings.config_dir / "tribal.yaml"
    existing: list[str] = [str(d) for d in settings.watch_dirs]

    if existing:
        for d in existing:
            _info(f"  Watching: {d}")
        if not typer.confirm("\n     Add more directories?", default=False):
            return

    dirs = list(existing)
    while True:
        target = pick_directory()
        if target is None:
            break

        if str(target) in dirs:
            _warn(f"Already added: {target}")
            continue

        dirs.append(str(target))
        _ok(f"Added: {target}")

        if not typer.confirm("     Add another directory?", default=True):
            break

    if not dirs:
        _warn("No directories set. Add later with: tribal watch add")
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
    _ok(f"Watching {len(dirs)} {noun}")
