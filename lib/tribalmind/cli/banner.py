"""Colored ASCII banner for the TribalMind CLI."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

# Theme: indigo-to-violet gradient matching the logo palette
LOGO_TOP_COLOR = "bold #818cf8"  # indigo-400
LOGO_MID_COLOR = "bold #a78bfa"  # violet-400
LOGO_BOT_COLOR = "bold #c084fc"  # purple-400
BORDER_STYLE = "#6366f1"  # indigo-500
TAGLINE_STYLE = "#a5b4fc"  # indigo-300
ACCENT_STYLE = "bold #34d399"  # emerald-400

# Block-drawing chars (█╗║ etc.) are often double-width in terminals; use explicit
# width so the panel doesn't wrap. Max line length 78 → 78*2 + border/padding.
LOGO_DISPLAY_WIDTH = 162

LOGO_RAW = [
    "  ████████╗██████╗ ██╗██████╗  █████╗ ██╗     ███╗   ███╗██╗███╗  ██╗██████╗",
    "  ╚══██╔══╝██╔══██╗██║██╔══██╗██╔══██╗██║     ████╗ ████║██║████╗ ██║██╔══██╗",
    "     ██║   ██████╔╝██║██████╔╝███████║██║     ██╔████╔██║██║██╔██╗██║██║  ██║",
    "     ██║   ██╔══██╗██║██╔══██╗██╔══██║██║     ██║╚██╔╝██║██║██║╚████║██║  ██║",
    "     ██║   ██║  ██║██║██████╔╝██║  ██║███████╗██║ ╚═╝ ██║██║██║ ╚███║██████╔╝",
    "     ╚═╝   ╚═╝  ╚═╝╚═╝╚═════╝ ╚═╝  ╚═╝╚══════╝╚═╝     ╚═╝╚═╝╚═╝  ╚══╝╚═════╝ ",
]

# Gradient color per line (top → bottom: indigo → violet → purple)
LOGO_GRADIENT = [
    LOGO_TOP_COLOR,
    LOGO_TOP_COLOR,
    LOGO_MID_COLOR,
    LOGO_MID_COLOR,
    LOGO_BOT_COLOR,
    LOGO_BOT_COLOR,
]

LOGO_COMPACT = (
    "[bold #818cf8]Tribal[/][bold #c084fc]Mind[/]"
    " [#a5b4fc]— Federated Developer Knowledge Agent[/]"
)


def print_banner(*, compact: bool = False) -> None:
    """Print the TribalMind logo to the console."""
    console = Console()
    if compact:
        console.print(LOGO_COMPACT + "\n")
    else:
        logo_lines = [
            Text(line, style=color)
            for line, color in zip(LOGO_RAW, LOGO_GRADIENT)
        ]
        tagline = Text(
            "Observes terminal activity · shares validated fixes across your team",
            style=TAGLINE_STYLE,
        )
        content = Group(
            *logo_lines,
            Text(),
            tagline,
        )
        panel = Panel(
            content,
            border_style=BORDER_STYLE,
            padding=(0, 1),
            expand=False,
            width=LOGO_DISPLAY_WIDTH,
        )
        console.print(panel)
        console.print()
