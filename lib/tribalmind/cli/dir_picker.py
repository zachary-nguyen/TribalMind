"""Interactive directory picker with arrow-key navigation and coloured UI."""

from __future__ import annotations

from pathlib import Path

import questionary
from questionary import Choice, Separator, Style

# Coloured style: pointer and highlighted in cyan/green, instruction dim
PICKER_STYLE = Style([
    ("qmark", "fg:cyan bold"),
    ("question", "bold fg:yellow"),
    ("pointer", "fg:cyan bold"),
    ("highlighted", "fg:cyan bold"),
    ("selected", "fg:green"),
    ("separator", "fg:ansibrightblack"),
    ("instruction", "fg:ansibrightblack italic"),
    ("text", ""),
    ("dir", "fg:cyan"),
    ("action", "fg:green bold"),
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
