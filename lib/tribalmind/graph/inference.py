"""Inference Node (stub) - detects fixes and proposes solutions.

Full implementation will:
1. If has_known_fix: extract the fix from matched memories
2. Else: use Backboard message API to send error + context to LLM for analysis
"""

from __future__ import annotations

from tribalmind.graph.state import TribalState


async def inference_node(state: TribalState) -> dict:
    """LangGraph node: analyze context and suggest fixes."""
    suggested_fix: str | None = None
    fix_confidence = 0.0

    if state.get("has_known_fix") and state.get("context"):
        context = state["context"]
        # Extract the best matching fix from local or team results
        for match in [*context.local_matches, *context.team_matches]:
            if hasattr(match, "fix_text") and match.fix_text:
                suggested_fix = match.fix_text
                fix_confidence = getattr(match, "relevance_score", 0.7)
                break

    # TODO: If no known fix found, use Backboard's message API to query an LLM
    # for fix suggestions based on the error context.

    return {
        "suggested_fix": suggested_fix,
        "fix_confidence": fix_confidence,
        "log": [
            f"inference: fix={'yes' if suggested_fix else 'no'} confidence={fix_confidence:.2f}"
        ],
    }
