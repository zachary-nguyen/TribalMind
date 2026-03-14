"""UI Node - renders Rich insight panels to the daemon console/log.

Outputs a formatted panel showing:
- Error type and package
- Suggested fix command
- Confidence score (color-coded)
- Source of the fix (local history / team knowledge / upstream)

The rendered output appears in the daemon console (foreground mode) and log file
(streamed to the web UI via SSE).
"""

from __future__ import annotations

import io
import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from tribalmind.graph.state import ContextResult, TribalState

logger = logging.getLogger(__name__)


def _confidence_label(confidence: float) -> Text:
    """Return a color-coded confidence label."""
    pct = int(confidence * 100)
    if confidence >= 0.8:
        return Text(f"{pct}% (high)", style="bold green")
    if confidence >= 0.5:
        return Text(f"{pct}% (medium)", style="bold yellow")
    return Text(f"{pct}% (low)", style="bold red")


def _determine_source(context: ContextResult | None) -> str:
    """Determine where the fix came from."""
    if context is None:
        return "unknown"

    if context.local_matches:
        for m in context.local_matches:
            if hasattr(m, "fix_text") and m.fix_text:
                return "local history"

    if context.team_matches:
        for m in context.team_matches:
            if hasattr(m, "fix_text") and m.fix_text:
                return "team knowledge"

    if context.upstream_info:
        return "upstream (GitHub)"

    return "inference"


def render_insight_panel(state: TribalState) -> str:
    """Render a Rich insight panel and return it as a string."""
    error_type = state.get("error_type", "Unknown error")
    package = state.get("error_package", "")
    fix = state.get("suggested_fix", "")
    confidence = state.get("fix_confidence", 0.0)
    context = state.get("context")
    promoted = state.get("promoted", False)
    source = _determine_source(context)

    # Build info table
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("key", style="dim", width=12)
    table.add_column("value")

    table.add_row("Error", Text(error_type, style="bold red"))
    if package:
        table.add_row("Package", Text(package, style="#a78bfa"))
    table.add_row("Confidence", _confidence_label(confidence))
    table.add_row("Source", Text(source, style="dim"))
    if fix:
        table.add_row("Fix", Text(fix, style="bold white"))
    if promoted:
        table.add_row("Shared", Text("promoted to team", style="#34d399"))

    panel = Panel(
        table,
        title="[bold #818cf8]TribalMind Insight[/bold #818cf8]",
        border_style="#6366f1",
        padding=(1, 2),
    )

    # Render to string
    buf = io.StringIO()
    console = Console(file=buf, width=80, force_terminal=True)
    console.print(panel)
    return buf.getvalue()


async def ui_node(state: TribalState) -> dict:
    """LangGraph node: display insight panel to the user."""
    displayed = False
    fix = state.get("suggested_fix")
    confidence = state.get("fix_confidence", 0.0)
    context = state.get("context")

    # Show panel if we have a fix or at least context matches to report
    has_content = (fix and confidence > 0.3) or (
        context and context.has_matches and not fix
    )

    rendered: str | None = None
    if has_content:
        rendered = render_insight_panel(state)
        # Log each line so it appears in daemon console and log file
        for line in rendered.splitlines():
            if line.strip():
                logger.info(line)
        displayed = True

    source = _determine_source(state.get("context")) if displayed else "none"
    return {
        "displayed": displayed,
        "rendered_insight": rendered,
        "log": [f"ui: displayed={displayed} source={source}"],
    }
