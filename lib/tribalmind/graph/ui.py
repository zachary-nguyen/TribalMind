"""UI/Interaction Node (stub) - renders Rich insight boxes in the terminal.

Full implementation will:
1. Render a Rich Panel with error summary, suggested fix, confidence, source
2. Provide single-key shortcuts: [a]pply fix, [d]etails, [s]kip
3. Execute user-selected actions via subprocess
"""

from __future__ import annotations

from tribalmind.graph.state import TribalState


async def ui_node(state: TribalState) -> dict:
    """LangGraph node: display insight box to the user."""
    displayed = False

    if state.get("suggested_fix") and state.get("fix_confidence", 0) > 0.3:
        # TODO: Render Rich insight panel:
        # - Error type and package
        # - Suggested fix command
        # - Confidence score
        # - Source (local history / team knowledge / upstream)
        # - Action shortcuts: [a]pply, [d]etails, [s]kip
        displayed = True

    return {
        "displayed": displayed,
        "log": [f"ui: displayed={displayed}"],
    }
