"""Promotion Node - trust scoring and local-to-global knowledge promotion.

Responsibilities:
1. Store validated fixes as Backboard memories on the project assistant
2. Increment trust_score when a fix is seen again (reinforcement)
3. Promote to org assistant when trust threshold is met and team sharing is on
"""

from __future__ import annotations

import logging

from tribalmind.backboard.client import BackboardClient, BackboardError, create_client
from tribalmind.backboard.memory import (
    MemoryEntry,
    add_memory,
    encode_memory,
    search_memories,
    update_memory,
)
from tribalmind.config.settings import get_settings
from tribalmind.graph.state import TribalState

logger = logging.getLogger(__name__)

# Default trust increment per occurrence
TRUST_INCREMENT = 1.0


async def _find_existing_memory(
    client: BackboardClient,
    assistant_id: str,
    error_signature: str,
    search_query: str = "",
) -> MemoryEntry | None:
    """Search for an existing memory matching this error signature.

    Uses semantic search with meaningful text (error type + package),
    then confirms the match by comparing the stored sig field.
    """
    query = search_query or error_signature
    results = await search_memories(client, assistant_id, query, limit=5)
    for entry in results:
        # Exact match on error signature — this is the real dedup key
        if entry.sig and entry.sig == error_signature:
            return entry
    return None


def _build_search_query(state: TribalState) -> str:
    """Build a meaningful search query for semantic memory lookup."""
    parts = []
    if state.get("error_type"):
        parts.append(state["error_type"])
    if state.get("error_package"):
        parts.append(state["error_package"])
    if not parts:
        # Fall back to command text for searchability
        event = state.get("event")
        if event:
            parts.append(event.command[:80])
    return " ".join(parts) if parts else ""


async def _store_or_update_memory(
    client: BackboardClient,
    assistant_id: str,
    state: TribalState,
) -> tuple[str, float]:
    """Store a new memory or update an existing one with incremented trust.

    Returns (memory_id, new_trust_score).
    """
    error_sig = state.get("error_signature", "")
    search_query = _build_search_query(state)
    existing = await _find_existing_memory(
        client, assistant_id, error_sig, search_query=search_query
    )

    if existing and existing.memory_id:
        # Increment trust on the existing memory
        new_trust = existing.trust_score + TRUST_INCREMENT
        updated_content = encode_memory(
            existing.category or "error",
            package=existing.package or state.get("error_package", ""),
            version=existing.version,
            error_text=existing.error_text,
            fix_text=state.get("suggested_fix") or existing.fix_text,
            confidence=state.get("fix_confidence", existing.confidence),
            trust_score=new_trust,
            sig=error_sig,
        )
        await update_memory(client, assistant_id, existing.memory_id, updated_content)
        logger.info(
            "Updated memory %s, trust %.1f -> %.1f",
            existing.memory_id,
            existing.trust_score,
            new_trust,
        )
        return existing.memory_id, new_trust

    # Create new memory
    error_text = state.get("error_type", "")
    if state.get("error_package"):
        error_text += f" {state['error_package']}"
    content = encode_memory(
        "error",
        package=state.get("error_package", ""),
        error_text=error_text or error_sig,
        fix_text=state.get("suggested_fix", ""),
        confidence=state.get("fix_confidence", 0.0),
        trust_score=TRUST_INCREMENT,
        sig=error_sig,
    )
    result = await add_memory(client, assistant_id, content)
    memory_id = result.get("memory_id", result.get("id", ""))
    logger.info("Created new memory %s with trust %.1f", memory_id, TRUST_INCREMENT)
    return memory_id, TRUST_INCREMENT


async def _promote_to_org(
    client: BackboardClient,
    org_assistant_id: str,
    state: TribalState,
    trust_score: float,
) -> bool:
    """Copy a high-trust memory to the org assistant for team sharing."""
    error_sig = state.get("error_signature", "")
    search_query = _build_search_query(state)
    existing = await _find_existing_memory(
        client, org_assistant_id, error_sig, search_query=search_query
    )
    if existing:
        logger.info("Memory already exists in org assistant, skipping promotion")
        return False

    error_text = state.get("error_type", "")
    if state.get("error_package"):
        error_text += f" {state['error_package']}"
    content = encode_memory(
        "error",
        package=state.get("error_package", ""),
        error_text=error_text or error_sig,
        fix_text=state.get("suggested_fix", ""),
        confidence=state.get("fix_confidence", 0.0),
        trust_score=trust_score,
        sig=error_sig,
    )
    await add_memory(client, org_assistant_id, content)
    logger.info("Promoted memory to org assistant %s", org_assistant_id)
    return True


async def promotion_node(state: TribalState) -> dict:
    """LangGraph node: handle fix storage and trust-based promotion."""
    promoted = False
    suggested_fix = state.get("suggested_fix")

    if not suggested_fix:
        return {
            "promoted": False,
            "log": ["promotion: skipped (no fix to store)"],
        }

    settings = get_settings()
    project_id = settings.project_assistant_id

    if not project_id:
        return {
            "promoted": False,
            "log": ["promotion: skipped (no project assistant configured)"],
        }

    try:
        async with create_client() as client:
            # 1. Store / update memory with trust scoring
            memory_id, trust_score = await _store_or_update_memory(
                client, project_id, state
            )

            # 2. Promote to org if trust threshold met and team sharing enabled
            if (
                settings.team_sharing_enabled
                and settings.org_assistant_id
                and trust_score >= settings.trust_threshold
            ):
                promoted = await _promote_to_org(
                    client, settings.org_assistant_id, state, trust_score
                )

    except BackboardError as e:
        logger.error("Promotion failed: %s", e)
        return {
            "promoted": False,
            "log": [f"promotion: error ({e.detail})"],
        }

    return {
        "promoted": promoted,
        "log": [
            f"promotion: stored memory={memory_id} trust={trust_score:.1f} "
            f"promoted={promoted}"
        ],
    }
