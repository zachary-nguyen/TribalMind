"""Colored ASCII banner for the TribalMind CLI."""

from __future__ import annotations

from rich.console import Console, Group
from rich.panel import Panel
from rich.text import Text

# Theme: single accent for logo (readable), border and tagline muted
LOGO_COLOR = "bold cyan"
BORDER_STYLE = "cyan"
TAGLINE_STYLE = "dim"

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

LOGO_COMPACT = (
    "[bold cyan]Tribal[/][bold cyan]Mind[/] [dim]— Federated Developer Knowledge Agent[/dim]"
)


def print_banner(*, compact: bool = False) -> None:
    """Print the TribalMind logo to the console."""
    console = Console()
    if compact:
        console.print(LOGO_COMPACT + "\n")
    else:
        logo_lines = [Text(line, style=LOGO_COLOR) for line in LOGO_RAW]
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
