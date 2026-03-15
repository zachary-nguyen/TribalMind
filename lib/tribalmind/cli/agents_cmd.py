"""CLI command for generating agent integration files."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

# ── Agent definitions ────────────────────────────────────────────────────────

TRIBAL_SNIPPET = """\
## TribalMind — Project Memory

This project uses [TribalMind](https://github.com/zachary-nguyen/TribalMind) \
for shared knowledge persistence across agents and team members.

### When to recall

**IMPORTANT: When investigating issues, debugging, or answering "why does X \
happen" questions, ALWAYS run `tribal recall` FIRST before exploring the \
codebase or spawning exploration agents.** The answer is often already in \
shared memory and skipping this step wastes significant time.

Use `tribal recall` when:
- You're investigating an issue or unexpected behavior (check memory FIRST)
- You need context about the project or area you're working in
- You're stuck or unsure about the right approach
- You need context about a past decision, convention, or known issue
- You're working in an unfamiliar part of the codebase

```bash
tribal recall --json "<describe what you need context on>"
```

### When to remember

As you work, **proactively** store knowledge the team would benefit from — \
don't wait until the end of a task or for the user to ask.

**IMPORTANT: After completing any change, immediately ask yourself: "Would \
this knowledge help a teammate (or future me) avoid confusion or save time?" \
If yes, run `tribal remember` right away as part of completing the task — do \
NOT wait for the user to remind you.**

**Always remember when:**
- You change a config value and the user explains *why* (e.g. setting a flag \
to preserve data)
- You discover or apply a non-obvious fix, workaround, or gotcha
- The user shares reasoning behind a decision or convention
- You learn how modules connect or why things are built a certain way
- You encounter environment, config, or setup quirks
- You find surprising behavior during exploration or code review

**Do NOT remember** trivial changes, obvious fixes, or things already clear \
from the code itself.

```bash
tribal remember "<what you learned — be specific and include context>"
```

When you store a memory, briefly tell the user what was saved (e.g. "Saved to \
project memory: <summary>").

### Reference

- `--json` — structured output for programmatic use
- `--list` / `-l` — browse all memories without a search query (no cost)
- `--all` / `-a` — search across all repos in the account (cross-repo)
- Pipe via stdin: `echo "insight" | tribal remember`
"""

AGENTS: dict[str, dict] = {
    "CLAUDE.md": {
        "label": "Claude Code",
        "path": "CLAUDE.md",
        "section_marker": "## TribalMind",
    },
    ".cursorrules": {
        "label": "Cursor",
        "path": ".cursorrules",
        "section_marker": "## TribalMind",
    },
    ".windsurfrules": {
        "label": "Windsurf",
        "path": ".windsurfrules",
        "section_marker": "## TribalMind",
    },
    ".github/copilot-instructions.md": {
        "label": "GitHub Copilot",
        "path": ".github/copilot-instructions.md",
        "section_marker": "## TribalMind",
    },
    "AGENTS.md": {
        "label": "Generic (AGENTS.md)",
        "path": "AGENTS.md",
        "section_marker": "## TribalMind",
    },
}


def _detect_agents(root: Path) -> list[str]:
    """Return keys for agent config files that already exist in the project."""
    found = []
    for key, info in AGENTS.items():
        if (root / info["path"]).exists():
            found.append(key)
    return found


def _inject_snippet(file_path: Path, snippet: str, marker: str) -> str:
    """Append or replace the TribalMind section in a file.

    Returns: 'created', 'updated', or 'unchanged'.
    """
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")
        if marker in content:
            # Replace existing section: from marker to next ## heading or EOF
            start = content.index(marker)
            rest = content[start + len(marker) :]
            # Find the next same-level heading (## ) or EOF
            next_heading = -1
            for i, line in enumerate(rest.split("\n")):
                if i > 0 and line.startswith("## "):
                    next_heading = len("\n".join(rest.split("\n")[:i]))
                    break
            if next_heading == -1:
                # Replace to end of file
                new_content = content[:start].rstrip() + "\n\n" + snippet.rstrip() + "\n"
            else:
                after = rest[next_heading:]
                new_content = (
                    content[:start].rstrip()
                    + "\n\n"
                    + snippet.rstrip()
                    + "\n\n"
                    + after.lstrip()
                )
            if new_content.strip() == content.strip():
                return "unchanged"
            file_path.write_text(new_content, encoding="utf-8")
            return "updated"
        else:
            # Append
            separator = "\n\n" if content.rstrip() else ""
            file_path.write_text(
                content.rstrip() + separator + snippet.rstrip() + "\n",
                encoding="utf-8",
            )
            return "updated"
    else:
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(snippet.rstrip() + "\n", encoding="utf-8")
        return "created"


def _find_project_root() -> Path:
    """Walk up from CWD to find the nearest .git directory, or fall back to CWD."""
    current = Path.cwd().resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return current


def setup_agents(
    agents: list[str] | None = typer.Option(  # noqa: UP007
        None,
        "--agent",
        "-a",
        help="Agent config files to generate (e.g. CLAUDE.md, .cursorrules). "
        "Can be repeated. If omitted, auto-detects existing files or prompts.",
    ),
    all_agents: bool = typer.Option(
        False,
        "--all",
        help="Generate snippets for all supported agents.",
    ),
    project_root: str | None = typer.Option(  # noqa: UP007
        None,
        "--project-root",
        "-p",
        help="Project root path (defaults to git root or CWD).",
    ),
    list_agents: bool = typer.Option(
        False,
        "--list",
        "-l",
        help="List supported agent config files and exit.",
    ),
) -> None:
    """Generate agent integration files so AI coding agents use TribalMind.

    Writes a TribalMind usage snippet into agent instruction files (CLAUDE.md,
    .cursorrules, etc.) so agents automatically recall and remember knowledge.

    \b
    Examples:
        tribal setup-agents                         # Auto-detect or prompt
        tribal setup-agents -a CLAUDE.md            # Just Claude Code
        tribal setup-agents -a CLAUDE.md -a .cursorrules
        tribal setup-agents --all                   # All supported agents
        tribal setup-agents --list                  # Show supported agents
    """
    if list_agents:
        console.print("[bold]Supported agent config files:[/bold]\n")
        for key, info in AGENTS.items():
            console.print(f"  [#a78bfa]{key}[/#a78bfa]  — {info['label']}")
        console.print()
        raise typer.Exit()

    root = Path(project_root).resolve() if project_root else _find_project_root()

    # Determine which agents to target
    if all_agents:
        targets = list(AGENTS.keys())
    elif agents:
        # Validate provided agent names
        targets = []
        for a in agents:
            if a not in AGENTS:
                console.print(f"[red]Unknown agent:[/red] {a}")
                console.print(f"[dim]Supported: {', '.join(AGENTS.keys())}[/dim]")
                raise typer.Exit(1)
            targets.append(a)
    else:
        # Auto-detect existing files, then prompt for any additional
        detected = _detect_agents(root)
        if detected:
            labels = ", ".join(AGENTS[k]["label"] for k in detected)
            console.print(f"[dim]Detected existing agent files:[/dim] {labels}")
            targets = detected
        else:
            # Nothing detected — ask which to create
            console.print("[bold]Which agent config files would you like to create?[/bold]\n")
            for i, (key, info) in enumerate(AGENTS.items(), 1):
                console.print(f"  [#a78bfa]{i}.[/#a78bfa] {key}  — {info['label']}")
            console.print()
            choices = typer.prompt(
                "Enter numbers separated by commas (e.g. 1,2), or 'all'",
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
                    elif part in AGENTS:
                        targets.append(part)
                if not targets:
                    console.print("[red]No valid selections.[/red]")
                    raise typer.Exit(1)

    # Write snippets
    console.print()
    for key in targets:
        info = AGENTS[key]
        file_path = root / info["path"]
        result = _inject_snippet(file_path, TRIBAL_SNIPPET, info["section_marker"])
        if result == "created":
            console.print(f"  [green]created[/green]  {info['path']}  ({info['label']})")
        elif result == "updated":
            console.print(f"  [yellow]updated[/yellow]  {info['path']}  ({info['label']})")
        else:
            console.print(f"  [dim]unchanged[/dim]  {info['path']}  ({info['label']})")

    console.print()
    console.print("[green]Done![/green] Agents will now use tribal recall/remember automatically.")
