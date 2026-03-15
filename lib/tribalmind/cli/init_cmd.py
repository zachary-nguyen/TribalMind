"""CLI command for initializing a TribalMind project."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

console = Console()


def _find_git_root() -> Path | None:
    """Walk up from CWD to find the nearest .git directory."""
    current = Path.cwd().resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


async def _setup_assistant(project_root: str) -> dict:
    """Create or find the Backboard assistant for this project."""
    from tribalmind.backboard.assistants import get_or_create_project_assistant
    from tribalmind.backboard.client import create_client

    async with create_client() as client:
        return await get_or_create_project_assistant(client, project_root)


def _get_global_config_path() -> Path:
    """Return the user-level tribal.yaml path."""
    import platformdirs

    config_dir = Path(platformdirs.user_config_dir("tribalmind"))
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "tribal.yaml"


def init(
    api_key: str | None = typer.Option(  # noqa: UP007
        None, "--api-key", "-k",
        help="Backboard API key (for non-interactive / agent use).",
    ),
    project_root: str | None = typer.Option(  # noqa: UP007
        None, "--project-root", "-p",
        help="Project root path (defaults to git root or CWD).",
    ),
    global_init: bool = typer.Option(
        False, "--global", "-g",
        help="Set up a user-level default config. All repos without their own "
        "tribal.yaml will inherit from it.",
    ),
    llm_provider_opt: str | None = typer.Option(  # noqa: UP007
        None, "--llm-provider",
        help="LLM provider: anthropic, openai, or google (for non-interactive use).",
    ),
    model_name_opt: str | None = typer.Option(  # noqa: UP007
        None, "--model-name",
        help="LLM model name (for non-interactive use).",
    ),
) -> None:
    """Initialize TribalMind for the current project (or globally).

    Sets up the Backboard API key (if needed) and creates a Backboard assistant
    for storing memories.

    \b
    Modes:
        tribal init            # per-repo: config in ./tribal.yaml
        tribal init --global   # user-level: config in ~/.config/tribalmind/
                               #   all repos inherit unless they have their own

    \b
    Examples:
        tribal init                        # set up this repo
        tribal init --global               # set up user-level default
        tribal init --api-key sk-xxx       # non-interactive
        tribal init --project-root /path   # specific project
    """
    from tribalmind.cli.banner import print_banner
    print_banner(compact=bool(api_key))

    from tribalmind.backboard.client import BackboardError
    from tribalmind.cli.config_cmd import _get_config_path, _load_config_file, _save_config_file
    from tribalmind.config.credentials import (
        BACKBOARD_API_KEY,
        get_backboard_api_key,
        set_credential,
    )
    from tribalmind.config.settings import clear_settings_cache

    # Step 1: Ensure API key is configured
    if api_key:
        set_credential(BACKBOARD_API_KEY, api_key)
        clear_settings_cache()
        console.print("[green]API key stored.[/green]")
    elif not get_backboard_api_key():
        api_key = typer.prompt("Enter your Backboard API key", hide_input=True)
        api_key = api_key.strip() if api_key else ""
        if not api_key or len(api_key) < 8:
            console.print("[red]Invalid API key.[/red]")
            console.print(
                "[dim]Paste not working? Use:[/dim] "
                "[#a78bfa]tribal init --api-key YOUR_KEY[/#a78bfa]"
            )
            raise typer.Exit(1)

        # Validate the key against the API before storing
        try:
            from tribalmind.backboard.client import BackboardClient, BackboardError
            from tribalmind.config.settings import get_settings

            settings = get_settings()

            async def _validate_key() -> None:
                async with BackboardClient(settings.backboard_base_url, api_key) as c:
                    await c.get("/assistants")

            asyncio.run(_validate_key())
        except BackboardError as e:
            if e.status_code == 401:
                console.print(f"[red]API key rejected by Backboard:[/red] {e.detail}")
                console.print(
                    "[dim]Paste not working? Use:[/dim] "
                    "[#a78bfa]tribal init --api-key YOUR_KEY[/#a78bfa]"
                )
                raise typer.Exit(1)
            # Other errors (network, etc.) — don't block init, key format is fine

        set_credential(BACKBOARD_API_KEY, api_key)
        clear_settings_cache()
        console.print("[green]API key stored in system keyring.[/green]")

    # Step 2: Determine scope and project root
    if global_init:
        # Global mode: use "global" as the project root identifier
        root_label = "global (all projects)"
        assistant_root = "global"
    else:
        if project_root:
            root = Path(project_root).resolve()
        else:
            root = _find_git_root() or Path.cwd()
        root_label = str(root)
        assistant_root = str(root)

    # Step 2b: LLM provider/model selection
    llm_presets = {
        "1": ("anthropic", "claude-sonnet-4-6", "Anthropic — Claude Sonnet 4.6"),
        "2": ("openai", "gpt-5-codex", "OpenAI — GPT-5 Codex"),
        "3": ("google", "gemini-3.1-flash-lite-preview", "Google — Gemini 3.1 Flash Lite"),
    }
    llm_provider = llm_provider_opt
    model_name = model_name_opt

    if llm_provider and model_name:
        pass  # CLI flags provided, skip interactive
    elif not api_key:
        console.print()
        console.print("[bold]Which LLM should TribalMind use for parsing memories?[/bold]")
        console.print()
        for num, (_, _, label) in llm_presets.items():
            console.print(f"  [#a78bfa]{num}.[/#a78bfa] {label}")
        console.print("  [#a78bfa]4.[/#a78bfa] Custom provider/model")
        console.print()
        choice = typer.prompt("  Choose", default="1").strip()

        if choice in llm_presets:
            llm_provider, model_name, _ = llm_presets[choice]
        elif choice == "4":
            llm_provider = typer.prompt("  Provider (anthropic/openai/google)")
            model_name = typer.prompt("  Model name")
        else:
            # Default to anthropic
            llm_provider, model_name, _ = llm_presets["1"]

        console.print(f"  [dim]Using:[/dim] {llm_provider}/{model_name}")

    # Step 3: Create or find the Backboard assistant
    try:
        assistant = asyncio.run(_setup_assistant(assistant_root))
    except BackboardError as e:
        console.print(f"[red]Backboard API error {e.status_code}:[/red] {e.detail}")
        raise typer.Exit(1)

    assistant_id = assistant.get("assistant_id", "")
    if not assistant_id:
        console.print("[red]Failed to create assistant — no ID returned.[/red]")
        raise typer.Exit(1)

    # Step 4: Save to tribal.yaml (global or per-repo)
    if global_init:
        config_path = _get_global_config_path()
    else:
        config_path = _get_config_path()
    data = _load_config_file(config_path)
    data["project_assistant_id"] = assistant_id
    if llm_provider:
        data["llm_provider"] = llm_provider
    if model_name:
        data["model_name"] = model_name
    if not global_init:
        data["project_root"] = str(root)
    _save_config_file(config_path, data)
    clear_settings_cache()

    console.print()
    if global_init:
        console.print("[green]TribalMind initialized globally[/green]")
        console.print(f"  [dim]assistant:[/dim] [#a78bfa]{assistant_id}[/#a78bfa]")
        console.print(f"  [dim]config:[/dim]    {config_path}")
        console.print()
        console.print(
            "  [dim]All repos will use this config unless they"
            " have their own tribal.yaml.[/dim]"
        )
        console.print(
            "  [dim]Run [bold]tribal init[/bold] inside a repo to"
            " override with a project-specific setup.[/dim]"
        )
    else:
        console.print(f"[green]TribalMind initialized for[/green] {root_label}")
        console.print(f"  [dim]assistant:[/dim] [#a78bfa]{assistant_id}[/#a78bfa]")
        console.print(f"  [dim]config:[/dim]    {config_path}")

    # Step 5: Offer to set up agent integration files
    console.print()
    if api_key:
        # Non-interactive mode (agent use) — skip the prompt
        pass
    elif typer.confirm(
        "Set up agent integration files (CLAUDE.md, .cursorrules, etc.)?",
        default=True,
    ):
        from tribalmind.cli.agents_cmd import (
            AGENTS,
            TRIBAL_SNIPPET,
            _detect_agents,
            _inject_snippet,
        )

        detected = _detect_agents(root)
        if detected:
            labels = ", ".join(AGENTS[k]["label"] for k in detected)
            console.print(f"  [dim]Detected existing agent files:[/dim] {labels}")
            targets = detected
        else:
            console.print()
            console.print("  [bold]Which agent config files would you like to create?[/bold]")
            console.print()
            for i, (key, info) in enumerate(AGENTS.items(), 1):
                console.print(f"    [#a78bfa]{i}.[/#a78bfa] {key}  — {info['label']}")
            console.print()
            choices = typer.prompt(
                "  Enter numbers separated by commas (e.g. 1,2), or 'all'",
                default="1",
            )
            if choices.strip().lower() == "all":
                targets = list(AGENTS.keys())
            else:
                keys_list = list(AGENTS.keys())
                targets = []
                for part in choices.split(","):
                    part = part.strip()
                    if part.isdigit():
                        idx = int(part) - 1
                        if 0 <= idx < len(keys_list):
                            targets.append(keys_list[idx])
                if not targets:
                    console.print("  [dim]Skipped agent setup.[/dim]")
                    targets = []

        for key in targets:
            info = AGENTS[key]
            file_path = root / info["path"]
            result = _inject_snippet(file_path, TRIBAL_SNIPPET, info["section_marker"])
            if result == "created":
                console.print(f"    [green]created[/green]  {info['path']}")
            elif result == "updated":
                console.print(f"    [yellow]updated[/yellow]  {info['path']}")

    console.print()
    console.print("[dim]Get started:[/dim]")
    console.print('  tribal remember "your first piece of knowledge"')
    console.print('  tribal recall "search query"')
