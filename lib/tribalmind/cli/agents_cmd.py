"""CLI command for generating agent integration files."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

# ── Shared building blocks ──────────────────────────────────────────────────

_RECALL_SECTION = """\
### When to recall

**Run `tribal recall` BEFORE investigating issues or exploring unfamiliar \
areas.** Check shared memory first — it often already has the answer and saves \
significant time.

**Recall when:**
1. The user asks **why** something works a certain way
2. The user reports a **bug, error, or unexpected behavior**
3. You need context about a **past decision, convention, or known issue**
4. You are **stuck or unsure** about the right approach
5. You are starting work in an **unfamiliar part of the codebase**

```bash
tribal recall --json "<describe what you need context on>"
```

**If recall returns no results**, or the query references a term you don't \
recognize in this repo, **automatically retry with `--all`** (cross-repo \
search). Do not ask the user — just do it.

```bash
tribal recall --all --json "<query>"
```"""

_REMEMBER_SECTION = """\
### MANDATORY: Remember after learning

**Rule: After completing any task where you learned something non-obvious, \
run `tribal remember` immediately — before responding to the user.**

**Run `tribal remember` when any of these happen:**
1. You **fix a bug** and the root cause was not obvious
2. The user explains **why** a config value, flag, or pattern exists
3. You discover a **workaround, gotcha, or surprising behavior**
4. You learn **how modules connect** or why something is built a certain way
5. You encounter **environment, setup, or config quirks**

**Skip** trivial changes, obvious fixes, or things already clear from the code.

```bash
tribal remember "<what you learned — be specific and include context>"
```

After storing, **tell the user** what was saved (e.g. "Saved to project \
memory: <summary>")."""

_REFERENCE_SECTION = """\
### Commands

| Command | Description |
|---------|-------------|
| `tribal recall "<query>"` | Search memory by semantic similarity |
| `tribal recall --all "<query>"` | Search across all repos in the account |
| `tribal recall --list` | Browse all memories (no query, no cost) |
| `tribal remember "<text>"` | Store knowledge to project memory |
| `tribal forget "<query>"` | Find and delete outdated memories |
| `tribal forget --id <id> --yes` | Delete a specific memory by ID |
| `tribal forget --all --yes` | Clear all memories |
| `tribal status` | Show project status and memory stats |

All commands support `--json` / `-j` for structured output.
Pipe via stdin: `echo "insight" | tribal remember`"""

# ── Provider-specific snippets ──────────────────────────────────────────────

SNIPPET_CLAUDE_CODE = f"""\
## TribalMind — Project Memory

This project uses [TribalMind](https://github.com/zachary-nguyen/TribalMind) \
for shared knowledge persistence across agents and team members.

### IMPORTANT: Dual-save rule

**Whenever you save to your native auto-memory (`~/.claude/`), you MUST also \
run `tribal remember` with the same insight in the same step — and vice versa.** \
Both writes happen together, every time. TribalMind is the shared team memory \
that all agents and team members can access.

{_RECALL_SECTION}

{_REMEMBER_SECTION}

{_REFERENCE_SECTION}"""

SNIPPET_DEFAULT = f"""\
## TribalMind — Project Memory

This project uses [TribalMind](https://github.com/zachary-nguyen/TribalMind) \
for shared knowledge persistence across agents and team members.

**You have no built-in persistent memory. TribalMind IS your memory.** Use it \
to persist and retrieve knowledge across sessions.

{_RECALL_SECTION}

{_REMEMBER_SECTION}

{_REFERENCE_SECTION}"""

AGENT_SNIPPETS: dict[str, str] = {
    "claude-code": SNIPPET_CLAUDE_CODE,
    "default": SNIPPET_DEFAULT,
}

# ── Agent definitions ────────────────────────────────────────────────────────

AGENTS: dict[str, dict] = {
    # ── Cross-agent standard (Cursor, Windsurf, VSCode Copilot, Claude Code) ──
    "AGENTS.md": {
        "label": "Cross-agent standard (Cursor, Windsurf, Copilot, Codex, Claude Code)",
        "path": "AGENTS.md",
        "section_marker": "## TribalMind",
        "snippet_key": "default",
    },
    # ── Claude Code specific ─────────────────────────────────────────────────
    "CLAUDE.md": {
        "label": "Claude Code (root)",
        "path": "CLAUDE.md",
        "section_marker": "## TribalMind",
        "snippet_key": "claude-code",
    },
    ".claude/CLAUDE.md": {
        "label": "Claude Code (repo)",
        "path": ".claude/CLAUDE.md",
        "section_marker": "## TribalMind",
        "snippet_key": "claude-code",
    },
    # ── Provider-specific (legacy, still supported) ──────────────────────────
    ".cursor/rules/tribalmind.md": {
        "label": "Cursor (project rules)",
        "path": ".cursor/rules/tribalmind.md",
        "section_marker": "## TribalMind",
        "snippet_key": "default",
    },
    ".cursorrules": {
        "label": "Cursor (legacy)",
        "path": ".cursorrules",
        "section_marker": "## TribalMind",
        "snippet_key": "default",
    },
    ".windsurfrules": {
        "label": "Windsurf (legacy)",
        "path": ".windsurfrules",
        "section_marker": "## TribalMind",
        "snippet_key": "default",
    },
    ".github/copilot-instructions.md": {
        "label": "GitHub Copilot",
        "path": ".github/copilot-instructions.md",
        "section_marker": "## TribalMind",
        "snippet_key": "default",
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

    Each agent provider receives a tailored prompt — for example, Claude Code
    is told to use tribal alongside its native memory, while other providers
    are told tribal IS their memory system.

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
            # Nothing detected — interactive checkbox picker
            from tribalmind.cli.prompts import checkbox

            agent_choices = [
                (f"{key}  — {info['label']}", key, key == "AGENTS.md")
                for key, info in AGENTS.items()
            ]
            selected = checkbox(
                "Which agent config files would you like to create?",
                choices=agent_choices,
            )

            if selected is None:
                raise typer.Exit()
            targets = selected
            if not targets:
                console.print("[red]No valid selections.[/red]")
                raise typer.Exit(1)

    # Write provider-specific snippets
    console.print()
    for key in targets:
        info = AGENTS[key]
        file_path = root / info["path"]
        snippet = AGENT_SNIPPETS[info["snippet_key"]]
        result = _inject_snippet(file_path, snippet, info["section_marker"])
        if result == "created":
            console.print(f"  [green]created[/green]  {info['path']}  ({info['label']})")
        elif result == "updated":
            console.print(f"  [yellow]updated[/yellow]  {info['path']}  ({info['label']})")
        else:
            console.print(f"  [dim]unchanged[/dim]  {info['path']}  ({info['label']})")

    console.print()
    console.print("[green]Done![/green] Agents will now use tribal recall/remember automatically.")
