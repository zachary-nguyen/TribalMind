"""Interactive directory picker with arrow-key navigation and coloured UI."""

from __future__ import annotations

from pathlib import Path

import questionary
from questionary import Choice, Separator, Style

# Coloured style: pointer and highlighted in violet, accents in emerald
PICKER_STYLE = Style([
    ("qmark", "fg:#a78bfa bold"),
    ("question", "bold fg:#c4b5fd"),
    ("pointer", "fg:#a78bfa bold"),
    ("highlighted", "fg:#a78bfa bold"),
    ("selected", "fg:#34d399"),
    ("separator", "fg:ansibrightblack"),
    ("instruction", "fg:ansibrightblack italic"),
    ("text", ""),
    ("dir", "fg:#818cf8"),
    ("action", "fg:#34d399 bold"),
    ("muted", "fg:ansibrightblack"),
])

# Sentinel values for special menu actions
PARENT = "__parent__"
SELECT_HERE = "__select__"
CANCEL = "__cancel__"


def _subdirs(path: Path) -> list[Path]:
    """List direct subdirectories, sorted; skip inaccessible."""
    try:
        return sorted(
            (d for d in path.iterdir() if d.is_dir()),
            key=lambda p: p.name.lower(),
        )
    except OSError:
        return []


def pick_directory(start_path: Path | None = None) -> Path | None:
    """Let the user navigate the filesystem and pick a directory.

    Uses arrow keys to move (.. to go up, enter a folder, or "Select this directory").
    Returns the chosen Path or None if cancelled.
    """
    current = (start_path or Path.cwd()).resolve()
    if not current.is_dir():
        current = current.parent

    while True:
        try:
            parent = current.parent
            can_go_up = parent != current
        except (OSError, ValueError):
            can_go_up = False
            parent = current

        subdirs = _subdirs(current)

        choices = []
        if can_go_up:
            choices.append(Choice(title=[("class:muted", "  ..  (parent)")], value=PARENT))
        choices.append(Separator())
        for d in subdirs:
            try:
                name = d.name + "/"
            except OSError:
                name = "?/"
            choices.append(Choice(title=[("class:dir", "  " + name)], value=str(d)))
        choices.append(Separator())
        choices.append(
            Choice(title=[("class:action", "  ✓ Select this directory")], value=SELECT_HERE),
        )
        choices.append(Choice(title=[("class:muted", "  Cancel")], value=CANCEL))

        prompt_message = str(current)
        if len(prompt_message) > 80:
            prompt_message = "..." + prompt_message[-77:]

        answer = questionary.select(
            prompt_message,
            choices=choices,
            style=PICKER_STYLE,
        ).ask()

        if answer is None:
            return None
        if answer == CANCEL:
            return None
        if answer == PARENT:
            current = parent
            continue
        if answer == SELECT_HERE:
            return current

        # Selected a subdirectory
        current = Path(answer)
        if not current.is_dir():
            current = current.parent
