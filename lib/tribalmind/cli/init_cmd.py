"""CLI command for initializing a TribalMind project."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from rich.console import Console

console = Console()

# Step label style
_STEP = "[bold #818cf8]"
_CHECK = "[bold #34d399]\u2714[/bold #34d399]"
_TOTAL_STEPS = 6


def _detect_shell() -> str | None:
    """Detect the user's current shell for completion installation."""
    import os
    import sys

    # Check SHELL env var (Unix)
    shell_env = os.environ.get("SHELL", "")
    if shell_env:
        name = Path(shell_env).name
        if name in ("bash", "zsh", "fish"):
            return name

    # Check Windows PowerShell
    if sys.platform == "win32":
        # Check if running inside PowerShell
        if os.environ.get("PSModulePath"):
            return "powershell"
        return "powershell"  # Default on Windows

    # Fallback: check COMSPEC or default
    return "bash"


def _find_git_root() -> Path | None:
    """Walk up from CWD to find the nearest .git directory."""
    current = Path.cwd().resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _ensure_gitignore(root: Path, entry: str = ".tribal/") -> bool:
    """Append *entry* to .gitignore if not already present. Returns True if modified."""
    gitignore = root / ".gitignore"
    if gitignore.exists():
        content = gitignore.read_text(encoding="utf-8")
        # Check if already covered (exact line match)
        if any(line.strip() == entry for line in content.splitlines()):
            return False
        # Append with a blank separator if file doesn't end with newline
        if content and not content.endswith("\n"):
            content += "\n"
        content += f"\n# TribalMind local config\n{entry}\n"
    else:
        content = f"# TribalMind local config\n{entry}\n"
    gitignore.write_text(content, encoding="utf-8")
    return True


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


def _step(num: int, label: str) -> None:
    """Print a step header."""
    console.print(f"\n{_STEP}Step {num}/{_TOTAL_STEPS}[/{_STEP[1:]}  [bold]{label}[/bold]")


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
        ".tribal/config.yaml will inherit from it.",
    ),
    llm_provider_opt: str | None = typer.Option(  # noqa: UP007
        None, "--llm-provider",
        help="LLM provider: anthropic, openai, or google (for non-interactive use).",
    ),
    model_name_opt: str | None = typer.Option(  # noqa: UP007
        None, "--model-name",
        help="LLM model name (for non-interactive use).",
    ),
    provider_opt: str | None = typer.Option(  # noqa: UP007
        None, "--provider",
        help="Memory provider: backboard, mem0 (for non-interactive / agent use).",
    ),
) -> None:
    """Initialize TribalMind for the current project (or globally).

    Sets up the memory provider and credentials, then creates a project
    assistant for storing memories.

    \b
    Modes:
        tribal init            # per-repo: config in ./.tribal/config.yaml
        tribal init --global   # user-level: config in ~/.config/tribalmind/
                               #   all repos inherit unless they have their own

    \b
    Examples:
        tribal init                        # set up this repo
        tribal init --global               # set up user-level default
        tribal init --api-key sk-xxx       # non-interactive (Backboard)
        tribal init --provider mem0        # use Mem0 backend
        tribal init --project-root /path   # specific project
    """
    from tribalmind.cli.banner import print_banner
    print_banner(compact=bool(api_key or provider_opt))

    from tribalmind.backboard.client import BackboardError
    from tribalmind.cli.config_cmd import _get_config_path, _load_config_file, _save_config_file
    from tribalmind.config.credentials import (
        BACKBOARD_API_KEY,
        get_backboard_api_key,
        set_credential,
    )
    from tribalmind.config.settings import clear_settings_cache
    from tribalmind.providers.factory import get_provider_choices

    # Non-interactive flag: True when --api-key or --provider is passed
    non_interactive = bool(api_key or provider_opt)

    def _store_api_key(key_value: str) -> None:
        """Store API key in keyring, falling back to config file."""
        stored = set_credential(BACKBOARD_API_KEY, key_value)
        if not stored:
            cfg_path = _get_config_path()
            cfg = _load_config_file(cfg_path)
            cfg["backboard_api_key"] = key_value.strip()
            _save_config_file(cfg_path, cfg)
        clear_settings_cache()

    # ── Step 1: Memory Provider Selection ──────────────────────────────────
    _step(1, "Memory Provider")

    # Check if re-running init on an existing project
    existing_config_path = _get_config_path()
    existing_config = _load_config_file(existing_config_path)
    existing_provider = existing_config.get("provider", "")

    if provider_opt:
        # Non-interactive: validate provider name
        available_names = [name for _, name, _ in get_provider_choices()]
        if provider_opt not in available_names:
            console.print(f"  [red]Unknown provider: {provider_opt}[/red]")
            console.print(f"  Available: {', '.join(available_names)}")
            raise typer.Exit(1)
        selected_provider = provider_opt
        console.print(f"  {_CHECK} Using [#a78bfa]{selected_provider}[/#a78bfa] provider")
    elif non_interactive:
        # --api-key without --provider → default to backboard
        selected_provider = existing_provider or "backboard"
        console.print(f"  {_CHECK} Using [#a78bfa]{selected_provider}[/#a78bfa] provider")
    else:
        from tribalmind.cli.prompts import select

        provider_choices = [
            (label, name)
            for label, name, coming_soon in get_provider_choices()
            if not coming_soon
        ]

        if existing_provider:
            console.print(
                f"  [dim]Current provider:[/dim] [#a78bfa]{existing_provider}[/#a78bfa]"
            )

        selected_provider = select(
            "  Select memory provider:",
            choices=provider_choices,
            default=existing_provider or "backboard",
        )

        if selected_provider is None:
            raise typer.Exit()
        console.print(f"  {_CHECK} Selected [#a78bfa]{selected_provider}[/#a78bfa]")

    # ── Step 2: Provider Credentials ───────────────────────────────────────
    _step(2, "Credentials")

    if selected_provider == "backboard":
        # Backboard API key setup (existing logic)
        if api_key:
            _store_api_key(api_key)
            console.print(f"  {_CHECK} Backboard API key stored.")
        elif get_backboard_api_key():
            console.print(f"  {_CHECK} Backboard API key already configured.")
        else:
            api_key = typer.prompt("  Enter your Backboard API key", hide_input=True)
            api_key = api_key.strip() if api_key else ""
            if not api_key or len(api_key) < 8:
                console.print("  [red]Invalid API key.[/red]")
                console.print(
                    "  [dim]Paste not working? Use:[/dim] "
                    "[#a78bfa]tribal init --api-key YOUR_KEY[/#a78bfa]"
                )
                raise typer.Exit(1)

            # Validate the key against the API before storing
            try:
                from tribalmind.backboard.client import BackboardClient
                from tribalmind.config.settings import get_settings

                settings = get_settings()

                async def _validate_key() -> None:
                    async with BackboardClient(settings.backboard_base_url, api_key) as c:
                        await c.get("/assistants")

                asyncio.run(_validate_key())
            except BackboardError as e:
                if e.status_code == 401:
                    console.print(
                        f"  [red]API key rejected by Backboard:[/red] {e.detail}"
                    )
                    console.print(
                        "  [dim]Paste not working? Use:[/dim] "
                        "[#a78bfa]tribal init --api-key YOUR_KEY[/#a78bfa]"
                    )
                    raise typer.Exit(1)
                # Other errors (network, etc.) — don't block init

            _store_api_key(api_key)
            console.print(f"  {_CHECK} Backboard API key stored.")

    elif selected_provider == "mem0":
        # Mem0 credentials
        from tribalmind.config.settings import get_settings

        settings = get_settings()
        mem0_key = settings.mem0_api_key

        if not mem0_key:
            import os

            mem0_key = os.environ.get("TRIBAL_MEM0_API_KEY", "")

        if mem0_key:
            console.print(f"  {_CHECK} Mem0 API key already configured.")
        else:
            mem0_key = typer.prompt("  Enter your Mem0 API key", hide_input=True)
            mem0_key = mem0_key.strip() if mem0_key else ""
            if not mem0_key or len(mem0_key) < 8:
                console.print("  [red]Invalid Mem0 API key.[/red]")
                raise typer.Exit(1)

        # Optional: org_id and project_id (Mem0 requires both or neither)
        mem0_org_id = settings.mem0_org_id
        mem0_project_id = settings.mem0_project_id

        if not non_interactive and not (mem0_org_id and mem0_project_id):
            mem0_org_id = typer.prompt(
                "  Mem0 org ID (optional, press Enter to skip)", default=""
            ).strip()
            if mem0_org_id:
                mem0_project_id = typer.prompt(
                    "  Mem0 project ID (required with org ID)", default=""
                ).strip()
                if not mem0_project_id:
                    console.print(
                        "  [yellow]Project ID is required when org ID is set."
                        " Skipping both.[/yellow]"
                    )
                    mem0_org_id = ""
            else:
                mem0_project_id = ""

        # Store Mem0 credentials in config file
        cfg_path = _get_config_path()
        cfg = _load_config_file(cfg_path)
        cfg["mem0_api_key"] = mem0_key
        if mem0_org_id and mem0_project_id:
            cfg["mem0_org_id"] = mem0_org_id
            cfg["mem0_project_id"] = mem0_project_id
        _save_config_file(cfg_path, cfg)
        clear_settings_cache()
        console.print(f"  {_CHECK} Mem0 credentials stored.")

    else:
        console.print(f"  {_CHECK} No credentials needed for {selected_provider}.")

    # ── Step 3: LLM provider ────────────────────────────────────────────────
    _step(3, "LLM Provider")

    # Determine scope and project root
    if global_init:
        root_label = "global (all projects)"
        assistant_root = "global"
    else:
        if project_root:
            root = Path(project_root).resolve()
        else:
            git_root = _find_git_root()
            if git_root:
                root = git_root
            else:
                root = Path.cwd()
                console.print(
                    f"\n  [yellow]\u26a0  No git repository detected.[/yellow]"
                    f"  Assistant will be named [bold]{root.name}[/bold] (directory name)."
                )
                from tribalmind.cli.prompts import confirm

                if not confirm("  Continue?", default=True):
                    console.print(
                        "\n  [dim]Run[/dim] [#a78bfa]tribal init[/#a78bfa]"
                        " [dim]from inside a git repo for repo-scoped memory.[/dim]"
                    )
                    raise typer.Exit()
        root_label = str(root)
        assistant_root = str(root)

    llm_presets = {
        "1": ("anthropic", "claude-sonnet-4-6", "Anthropic \u2014 Claude Sonnet 4.6"),
        "2": ("openai", "gpt-5-codex", "OpenAI \u2014 GPT-5 Codex"),
        "3": ("google", "gemini-3.1-flash-lite-preview", "Google \u2014 Gemini 3.1 Flash Lite"),
    }
    llm_provider = llm_provider_opt
    model_name = model_name_opt

    if llm_provider and model_name:
        console.print(f"  {_CHECK} Using {llm_provider}/{model_name}")
    elif not non_interactive:
        from tribalmind.cli.prompts import select

        llm_choices = [
            (label, num)
            for num, (_, _, label) in llm_presets.items()
        ]
        llm_choices.append(("Custom provider/model", "custom"))
        choice = select(
            "  Which LLM should TribalMind use for parsing memories?",
            choices=llm_choices,
            default=llm_choices[0][1],
        )

        if choice is None:
            raise typer.Exit()
        elif choice in llm_presets:
            llm_provider, model_name, _ = llm_presets[choice]
        else:
            llm_provider = typer.prompt("  Provider (anthropic/openai/google)")
            model_name = typer.prompt("  Model name")

        console.print(f"  {_CHECK} Using [#a78bfa]{llm_provider}/{model_name}[/#a78bfa]")

    # ── Step 4: Project Setup ──────────────────────────────────────────────
    _step(4, "Project Setup")

    assistant_id = ""
    if selected_provider == "backboard":
        # Backboard: create/find assistant via API
        try:
            assistant = asyncio.run(_setup_assistant(assistant_root))
        except BackboardError as e:
            console.print(
                f"  [red]Backboard API error {e.status_code}:[/red] {e.detail}"
            )
            raise typer.Exit(1)

        assistant_id = assistant.get("assistant_id", "")
        if not assistant_id:
            console.print("  [red]Failed to create assistant \u2014 no ID returned.[/red]")
            raise typer.Exit(1)
    else:
        # Non-Backboard providers: use git hash or directory name as project ID
        import hashlib

        if assistant_root == "global":
            assistant_id = "global"
        else:
            # Generate a stable project ID from the path
            assistant_id = hashlib.sha256(
                assistant_root.encode()
            ).hexdigest()[:12]
        console.print(f"  {_CHECK} Project ID: [#a78bfa]{assistant_id}[/#a78bfa]")

    # Save config (global: tribal.yaml in user config dir, per-repo: .tribal/config.yaml)
    if global_init:
        config_path = _get_global_config_path()
    else:
        config_path = _get_config_path()
    data = _load_config_file(config_path)
    data["provider"] = selected_provider
    data["project_assistant_id"] = assistant_id
    if llm_provider:
        data["llm_provider"] = llm_provider
    if model_name:
        data["model_name"] = model_name
    if not global_init:
        data["project_root"] = str(root)
    _save_config_file(config_path, data)
    clear_settings_cache()

    if global_init:
        console.print(f"  {_CHECK} Initialized globally")
        console.print(
            f"     [dim]provider:[/dim]  [#a78bfa]{selected_provider}[/#a78bfa]"
        )
        console.print(f"     [dim]assistant:[/dim] [#a78bfa]{assistant_id}[/#a78bfa]")
        console.print(f"     [dim]config:[/dim]    {config_path}")
    else:
        console.print(f"  {_CHECK} Initialized for [bold]{root_label}[/bold]")
        console.print(
            f"     [dim]provider:[/dim]  [#a78bfa]{selected_provider}[/#a78bfa]"
        )
        console.print(f"     [dim]assistant:[/dim] [#a78bfa]{assistant_id}[/#a78bfa]")
        console.print(f"     [dim]config:[/dim]    {config_path}")

        # Ensure .tribal/ is gitignored
        if _find_git_root():
            if _ensure_gitignore(root):
                console.print(f"  {_CHECK} Added [bold].tribal/[/bold] to .gitignore")

    # ── Step 5: Agent integration files ─────────────────────────────────────
    _step(5, "Agent Integration")
    if non_interactive:
        console.print(f"  {_CHECK} Skipped (non-interactive mode)")
    else:
        from tribalmind.cli.prompts import confirm

        if confirm("  Set up agent integration files?", default=True):
            from tribalmind.cli.agents_cmd import (
                AGENT_SNIPPETS,
                AGENTS,
                _detect_agents,
                _inject_snippet,
            )
            from tribalmind.cli.prompts import checkbox

            detected = _detect_agents(root)
            if detected:
                targets = detected
            else:
                agent_choices = [
                    (f"{key}  \u2014 {info['label']}", key, key == "AGENTS.md")
                    for key, info in AGENTS.items()
                ]
                selected = checkbox(
                    "  Which agent config files would you like to create?",
                    choices=agent_choices,
                )

                if selected is None:
                    raise typer.Exit()
                targets = selected

            if targets:
                for key in targets:
                    info = AGENTS[key]
                    file_path = root / info["path"]
                    snippet = AGENT_SNIPPETS[info["snippet_key"]]
                    result = _inject_snippet(file_path, snippet, info["section_marker"])
                    if result == "created":
                        console.print(f"  {_CHECK} [green]created[/green]  {info['path']}")
                    elif result == "updated":
                        console.print(f"  {_CHECK} [yellow]updated[/yellow]  {info['path']}")
                    else:
                        console.print(f"  {_CHECK} [dim]unchanged[/dim]  {info['path']}")
            else:
                console.print("  [dim]Skipped \u2014 no files selected.[/dim]")
        else:
            console.print("  [dim]Skipped.[/dim]")

    # ── Step 6: Shell completions ────────────────────────────────────────────
    _step(6, "Shell Completions")
    if non_interactive:
        console.print(f"  {_CHECK} Skipped (non-interactive mode)")
        console.print(
            "     [dim]Install later with:[/dim] "
            "[#a78bfa]tribal --install-completion[/#a78bfa]"
        )
    else:
        from tribalmind.cli.prompts import confirm as _confirm_completion

        if _confirm_completion("  Install shell tab-completions?", default=False):
            import subprocess

            # Detect the user's shell
            shell_name = _detect_shell()
            if shell_name:
                try:
                    subprocess.run(
                        ["tribal", "--install-completion", shell_name],
                        check=True,
                        capture_output=True,
                    )
                    console.print(
                        f"  {_CHECK} Installed completions for "
                        f"[#a78bfa]{shell_name}[/#a78bfa]"
                    )
                    console.print(
                        "     [dim]Restart your shell to activate.[/dim]"
                    )
                except (subprocess.CalledProcessError, FileNotFoundError):
                    console.print(
                        "  [yellow]Could not install automatically.[/yellow]"
                    )
                    console.print(
                        "     [dim]Run manually:[/dim] "
                        f"[#a78bfa]tribal --install-completion {shell_name}[/#a78bfa]"
                    )
            else:
                console.print(
                    "  [yellow]Could not detect shell.[/yellow]"
                )
                console.print(
                    "     [dim]Run manually:[/dim] "
                    "[#a78bfa]tribal --install-completion bash[/#a78bfa]"
                )
        else:
            console.print("  [dim]Skipped.[/dim]")
            console.print(
                "     [dim]Install later with:[/dim] "
                "[#a78bfa]tribal --install-completion[/#a78bfa]"
            )

    # ── Done ────────────────────────────────────────────────────────────────
    console.print()
    console.print(f"[bold #34d399]Setup complete![/bold #34d399]  (provider: {selected_provider})")
    console.print()
    console.print("  [dim]Get started:[/dim]")
    console.print('  [#a78bfa]tribal remember[/#a78bfa] "your first piece of knowledge"')
    console.print('  [#a78bfa]tribal recall[/#a78bfa]   "search query"')
    console.print()
