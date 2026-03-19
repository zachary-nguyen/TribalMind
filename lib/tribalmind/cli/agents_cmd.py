"""CLI command for generating agent integration files."""

from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console

console = Console()

# ── Markers for auto-update detection ──────────────────────────────────────

MARKER_START = "<!-- tribalmind:start -->"
MARKER_END = "<!-- tribalmind:end -->"

# ── Shared building blocks ──────────────────────────────────────────────────

_RECALL_SECTION = """\
### FIRST STEP: Check shared memory

**Before you read code, run commands, or start investigating, run \
`tribal recall`.** This is your first action on every task — not optional, \
not situational.

**Anti-pattern:** Do NOT jump straight into `grep`, `find`, or reading files \
to investigate an issue. Check memory first — the answer may already be there.

**Query tip:** Include both what the task is *about* and what *kind of work* \
it is (e.g., `"auth token refresh | deployment process"`). This surfaces both \
relevant knowledge and stored workflows for that type of task.

```bash
tribal recall --json "<topic and task type>"
```

If recall returns nothing relevant, retry across all repos:

```bash
tribal recall --all --json "<query>"
```

Skip recall when the task is self-contained and unlikely to benefit from \
prior context — e.g., simple refactors, renaming, formatting, adding types, \
writing new code from a clear spec, or general questions unrelated to the project."""

_REMEMBER_SECTION = """\
### LAST STEP: Save what you learned

**After completing a task, check: did you discover WHY something works the way \
it does? If yes, run `tribal remember` before responding.**

```bash
tribal remember "<what you learned — be specific, include the why>"
```

Examples of what to save:
- Root cause of a bug (not the fix itself — the WHY)
- Reasoning behind a config value, pattern, or architecture choice
- A workaround or gotcha that is not obvious from the code
- How components connect in ways that surprised you

Do NOT save: obvious fixes, things already clear from reading the code, or \
trivial changes.

After saving, tell the user: "Saved to project memory: <summary>."."""

_REFERENCE_SECTION = """\
### Quick reference

```bash
tribal recall --json "<query>"        # Search project memory
tribal recall --all --json "<query>"  # Search across all repos
tribal recall --list                  # Browse all memories
tribal remember "<what you learned>"  # Save to project memory
```

Full commands: `tribal forget`, `tribal status` (run `tribal --help` for details).
All commands support `--json` / `-j` for structured output."""

# ── Provider-specific snippets ──────────────────────────────────────────────

SNIPPET_CLAUDE_CODE = f"""\
{MARKER_START}
## TribalMind — Shared Project Memory

**WORKFLOW: (1) `tribal recall` before investigating. \
(2) `tribal remember` after learning.**

This project uses [TribalMind](https://github.com/zachary-nguyen/TribalMind) \
for persistent shared memory across agents and team members. You MUST follow \
the recall/remember workflow below.

{_RECALL_SECTION}

{_REMEMBER_SECTION}

**Note for Claude Code:** When saving to your native memory (`~/.claude/`), \
also run `tribal remember` with the same insight. Both writes happen together.

{_REFERENCE_SECTION}
{MARKER_END}"""

SNIPPET_DEFAULT = f"""\
{MARKER_START}
## TribalMind — Shared Project Memory

**WORKFLOW: (1) `tribal recall` before investigating. \
(2) `tribal remember` after learning.**

You have no built-in persistent memory. TribalMind IS your memory — use it \
to persist and retrieve knowledge across sessions.

{_RECALL_SECTION}

{_REMEMBER_SECTION}

{_REFERENCE_SECTION}
{MARKER_END}"""

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

    Detection order:
    1. HTML markers (<!-- tribalmind:start --> / <!-- tribalmind:end -->)
    2. Legacy heading-based detection (## TribalMind ... next ## heading)
    3. Append if neither found

    Returns: 'created', 'updated', or 'unchanged'.
    """
    if file_path.exists():
        content = file_path.read_text(encoding="utf-8")

        # ── Strategy 1: HTML marker-based replacement ──────────────────
        if MARKER_START in content and MARKER_END in content:
            start = content.index(MARKER_START)
            end = content.index(MARKER_END) + len(MARKER_END)
            before = content[:start].rstrip()
            after = content[end:].lstrip()
            parts = [before, snippet.rstrip()]
            if after:
                parts.append(after)
            new_content = "\n\n".join(parts) + "\n"
            if new_content.strip() == content.strip():
                return "unchanged"
            file_path.write_text(new_content, encoding="utf-8")
            return "updated"

        # ── Strategy 2: Legacy heading-based replacement ───────────────
        if marker in content:
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

        # ── Strategy 3: Append ─────────────────────────────────────────
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
