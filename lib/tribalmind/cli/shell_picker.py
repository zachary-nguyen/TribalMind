"""Interactive multi-select shell picker for the terminal.

Arrow keys to navigate, Space/Enter to toggle, Enter on [Confirm] to finish.
"""

from __future__ import annotations

import sys


def _read_key() -> str:
    """Read a single keypress, returning a normalized string.

    Returns: "up", "down", "space", "enter", "q", or the character.
    """
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\x00", "\xe0"):
            # Arrow key or special — read the second byte
            ch2 = msvcrt.getwch()
            if ch2 == "H":
                return "up"
            if ch2 == "P":
                return "down"
            return ""
        if ch == "\r":
            return "enter"
        if ch == " ":
            return "space"
        return ch
    else:
        import termios
        import tty
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    if ch3 == "A":
                        return "up"
                    if ch3 == "B":
                        return "down"
                return ""
            if ch in ("\r", "\n"):
                return "enter"
            if ch == " ":
                return "space"
            if ch == "\x03":
                raise KeyboardInterrupt
            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


def pick_shells(shells: list[dict]) -> list[str]:
    """Show an interactive multi-select and return chosen shell names.

    Each item in *shells* must have: name, label, available, installed.
    Only available shells are shown. Already-installed shells are pre-checked.
    Returns list of shell names the user selected (for new installation).
    """
    items = [s for s in shells if s["available"]]
    if not items:
        return []

    checked = [s["installed"] for s in items]
    cursor = 0
    confirm_idx = len(items)  # virtual "Confirm" row

    _render(items, checked, cursor, confirm_idx, first=True)

    try:
        while True:
            key = _read_key()

            if key == "up":
                cursor = (cursor - 1) % (len(items) + 1)
            elif key == "down":
                cursor = (cursor + 1) % (len(items) + 1)
            elif key in ("space", "enter"):
                if cursor == confirm_idx:
                    # Confirm selection
                    break
                checked[cursor] = not checked[cursor]
            elif key == "q":
                # Cancel
                _clear_lines(len(items) + 3)
                return []

            _render(items, checked, cursor, confirm_idx)
    except KeyboardInterrupt:
        _clear_lines(len(items) + 3)
        return []

    _clear_lines(len(items) + 3)

    # Return names of newly selected (not already installed) shells
    return [
        items[i]["name"]
        for i in range(len(items))
        if checked[i] and not items[i]["installed"]
    ]


def _render(
    items: list[dict],
    checked: list[bool],
    cursor: int,
    confirm_idx: int,
    first: bool = False,
) -> None:
    """Draw the picker UI, overwriting previous render."""
    total_lines = len(items) + 3  # items + blank + confirm + hint

    if not first:
        _clear_lines(total_lines)

    for i, item in enumerate(items):
        pointer = ">" if i == cursor else " "
        box = "x" if checked[i] else " "
        label = item["label"]
        note = ""
        if item["installed"]:
            note = " \033[32m(installed)\033[0m"
        line = f"     {pointer} [{box}] {label}{note}"
        sys.stdout.write(line + "\n")

    sys.stdout.write("\n")
    pointer = ">" if cursor == confirm_idx else " "
    sys.stdout.write(f"     {pointer} \033[1mConfirm\033[0m\n")
    sys.stdout.write("     \033[2m\u2191\u2193 move  Space toggle  Enter select  q cancel\033[0m\n")
    sys.stdout.flush()


def _clear_lines(n: int) -> None:
    """Move cursor up n lines and clear each one."""
    for _ in range(n):
        sys.stdout.write("\033[A\033[2K")
    sys.stdout.flush()
