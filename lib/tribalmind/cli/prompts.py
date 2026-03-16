"""Interactive prompt helpers with TTY fallback.

Uses questionary for arrow-key navigation when a real terminal is available,
falls back to simple typer.prompt when running in tests, CI, or piped input.

Styled to match TribalMind's indigo/violet theme.
"""

from __future__ import annotations

import sys

import typer

# ── questionary theme (indigo/violet palette) ───────────────────────────────

_THEME = None


def _get_theme():
    global _THEME
    if _THEME is None:
        from questionary import Style

        _THEME = Style([
            ("qmark", "fg:#a78bfa bold"),         # ? marker — violet-400
            ("question", "fg:#e2e8f0 bold"),       # question text — slate-200
            ("pointer", "fg:#818cf8 bold"),         # > pointer — indigo-400
            ("highlighted", "fg:#a78bfa bold"),     # highlighted choice — violet-400
            ("selected", "fg:#34d399"),             # checked items — emerald-400
            ("separator", "fg:#6366f1"),            # separator line — indigo-500
            ("instruction", "fg:#94a3b8"),          # hint text — slate-400
            ("answer", "fg:#34d399 bold"),          # final answer — emerald-400
        ])
    return _THEME


def _has_tty() -> bool:
    """Return True when stdin/stdout are connected to a real terminal."""
    return hasattr(sys.stdin, "isatty") and sys.stdin.isatty()


def confirm(message: str, *, default: bool = True) -> bool:
    """Y/n confirm prompt, styled to match the theme."""
    if _has_tty():
        try:
            import questionary

            result = questionary.confirm(
                message,
                default=default,
                style=_get_theme(),
            ).ask()
            return result if result is not None else default
        except Exception:
            pass
    return typer.confirm(message, default=default)


def select(
    message: str,
    choices: list[tuple[str, str]],
    default: str | None = None,
) -> str | None:
    """Single-select prompt.  *choices* is a list of (label, value) tuples."""
    if _has_tty():
        try:
            import questionary

            q_choices = [
                questionary.Choice(label, value=value)
                for label, value in choices
            ]
            return questionary.select(
                message,
                choices=q_choices,
                default=default,
                style=_get_theme(),
                instruction="(arrow keys to move, enter to select)",
            ).ask()
        except Exception:
            pass  # fall through to simple prompt

    # Fallback: numbered list
    print(f"\n{message}\n")
    for i, (label, _) in enumerate(choices, 1):
        print(f"  {i}. {label}")
    print()
    raw = typer.prompt("Choose", default="1").strip()
    if raw.isdigit():
        idx = int(raw) - 1
        if 0 <= idx < len(choices):
            return choices[idx][1]
    return default or choices[0][1]


def checkbox(
    message: str,
    choices: list[tuple[str, str, bool]],
) -> list[str] | None:
    """Multi-select prompt.  *choices* is a list of (label, value, checked) tuples."""
    if _has_tty():
        try:
            import questionary

            q_choices = [
                questionary.Choice(label, value=value, checked=checked)
                for label, value, checked in choices
            ]
            return questionary.checkbox(
                message,
                choices=q_choices,
                style=_get_theme(),
                instruction="(arrow keys to move, space to select, enter to confirm)",
            ).ask()
        except Exception:
            pass  # fall through to simple prompt

    # Fallback: numbered list, comma-separated input
    print(f"\n{message}\n")
    defaults = []
    for i, (label, value, checked) in enumerate(choices, 1):
        marker = "*" if checked else " "
        print(f"  {i}. [{marker}] {label}")
        if checked:
            defaults.append(str(i))
    print()
    raw = typer.prompt(
        "Enter numbers separated by commas, or 'all'",
        default=",".join(defaults) if defaults else "1",
    ).strip()
    if raw.lower() == "all":
        return [value for _, value, _ in choices]
    selected = []
    for part in raw.split(","):
        part = part.strip()
        if part.isdigit():
            idx = int(part) - 1
            if 0 <= idx < len(choices):
                selected.append(choices[idx][1])
    return selected
