"""Context Node - multi-hop search across local, team, and upstream sources.

Search order:
1. Project-local Backboard memories (always)
2. Team/org Backboard memories (if team sharing enabled)
3. Upstream GitHub issues/releases (if package identified)
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from tribalmind.graph.state import ContextResult, TribalState

logger = logging.getLogger(__name__)


async def _search_local(
    assistant_id: str | None,
    query: str,
) -> list[Any]:
    """Search project-local memories in Backboard."""
    if not assistant_id:
        return []

    try:
        from tribalmind.backboard.client import create_client
        from tribalmind.backboard.memory import search_memories

        async with create_client() as client:
            return await search_memories(client, assistant_id, query, limit=5)
    except Exception as e:
        logger.warning("Local memory search failed: %s", e)
        return []


async def _search_team(
    org_assistant_id: str | None,
    query: str,
) -> list[Any]:
    """Search team/org memories in Backboard."""
    if not org_assistant_id:
        return []

    try:
        from tribalmind.backboard.client import create_client
        from tribalmind.backboard.memory import search_memories

        async with create_client() as client:
            return await search_memories(client, org_assistant_id, query, limit=5)
    except Exception as e:
        logger.warning("Team memory search failed: %s", e)
        return []


async def _check_upstream(
    package: str | None,
    error_type: str | None,
) -> dict[str, Any] | None:
    """Check upstream GitHub for related issues/releases."""
    if not package:
        return None

    try:
        from tribalmind.upstream.github import check_package_health

        return await check_package_health(package, error_type or "")
    except Exception as e:
        logger.warning("Upstream check failed: %s", e)
        return None


async def context_node(state: TribalState) -> dict:
    """LangGraph node: multi-hop context search."""
    from tribalmind.config.settings import get_settings

    settings = get_settings()

    # Build search query from error details
    parts = []
    if state.get("error_type"):
        parts.append(state["error_type"])
    if state.get("error_package"):
        parts.append(state["error_package"])
    if state.get("error_signature"):
        parts.append(state["error_signature"])
    query = " ".join(parts) if parts else state["event"].command

    # Run searches concurrently
    org_id = settings.org_assistant_id if settings.team_sharing_enabled else None
    local_task = _search_local(settings.project_assistant_id, query)
    team_task = _search_team(org_id, query)
    upstream_task = _check_upstream(state.get("error_package"), state.get("error_type"))

    local_results, team_results, upstream_info = await asyncio.gather(
        local_task, team_task, upstream_task,
    )

    context = ContextResult(
        local_matches=local_results,
        team_matches=team_results,
        upstream_info=upstream_info,
    )

    # Check if any match contains a known fix with high confidence
    has_known_fix = False
    for match in [*local_results, *team_results]:
        if hasattr(match, "fix_text") and match.fix_text and hasattr(match, "relevance_score"):
            if match.relevance_score > 0.8:
                has_known_fix = True
                break

    return {
        "context": context,
        "has_known_fix": has_known_fix,
        "log": [
            f"context: local={len(local_results)} team={len(team_results)} "
            f"upstream={'yes' if upstream_info else 'no'} known_fix={has_known_fix}"
        ],
    }
