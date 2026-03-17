"""Backboard memory management for storing and retrieving knowledge.

Memories are stored as JSON strings conforming to the MEMORY_SCHEMA.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from tribalmind.backboard.client import BackboardClient

# Valid memory categories.
VALID_CATEGORIES = frozenset({
    "fix", "convention", "architecture", "context", "decision", "tip", "workflow",
})

# Canonical schema for memory content. All memories must conform to this.
MEMORY_SCHEMA = {
    "category": "one of: fix, convention, architecture, context, decision, tip, workflow",
    "subject": "what this is about (e.g. 'auth module', 'CI pipeline', 'numpy 1.26')",
    "content": "the actual knowledge — insight, fix, pattern, or description",
}


@dataclass
class MemoryEntry:
    """Parsed representation of a Backboard memory."""

    raw_content: str
    memory_id: str = ""
    category: str = ""
    subject: str = ""
    content: str = ""
    relevance_score: float = 0.0  # from search results
    raw: dict[str, Any] = field(default_factory=dict)


def encode_memory(
    category: str,
    *,
    subject: str = "",
    content: str = "",
) -> str:
    """Encode structured data into a JSON memory content string."""
    return json.dumps({
        "category": category,
        "subject": subject,
        "content": content,
    })


def parse_memory(raw_content: str, raw: dict[str, Any] | None = None) -> MemoryEntry:
    """Parse a Backboard memory content string into a MemoryEntry."""
    entry = MemoryEntry(raw_content=raw_content, raw=raw or {})

    if raw:
        entry.memory_id = raw.get("memory_id", raw.get("id", ""))
        # Backboard returns a distance (lower = closer); convert to
        # similarity so that higher values = more relevant.
        distance = raw.get("score", raw.get("relevance", 0.0))
        entry.relevance_score = max(0.0, 1.0 - distance) if distance else 0.0

    # Try JSON format first
    try:
        data = json.loads(raw_content)
        if isinstance(data, dict):
            entry.category = data.get("category", "")
            entry.subject = data.get("subject", "")
            entry.content = data.get("content", "")
            # Legacy field migration
            if not entry.content:
                entry.content = data.get("fix_text", data.get("error_text", ""))
            if not entry.subject:
                entry.subject = data.get("package", "")
            return entry
    except (json.JSONDecodeError, TypeError):
        pass

    # Fallback: legacy pipe-delimited format for old memories
    import re

    cat_match = re.match(r"\[(\w+)\]", raw_content)
    if cat_match:
        entry.category = cat_match.group(1)

    for match in re.finditer(r"package=([\w.\-]+)", raw_content):
        entry.subject = match.group(1)

    fix_match = re.search(r"fix:\s*(.+?)(?:\s*\||$)", raw_content)
    if fix_match:
        entry.content = fix_match.group(1).strip()

    if not entry.content:
        pipe_sections = raw_content.split("|")
        if len(pipe_sections) >= 2:
            entry.content = pipe_sections[1].strip()

    return entry


async def add_memory(
    client: BackboardClient,
    assistant_id: str,
    content: str,
    metadata: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Add a memory to a Backboard assistant."""
    payload: dict[str, Any] = {"content": content}
    if metadata:
        payload["metadata"] = metadata
    return await client.post(
        f"/assistants/{assistant_id}/memories",
        json=payload,
    )


async def enforce_memory_limit(
    client: BackboardClient,
    assistant_id: str,
    max_memories: int,
) -> int:
    """Delete oldest memories if the assistant exceeds *max_memories*.

    Returns the number of memories pruned.
    """
    if max_memories <= 0:
        return 0

    entries = await list_memories(client, assistant_id)
    excess = len(entries) - max_memories
    if excess <= 0:
        return 0

    # Sort by created_at ascending so oldest come first.
    # Fall back to memory_id for entries missing a timestamp.
    entries.sort(key=lambda e: e.raw.get("created_at", ""))
    to_delete = entries[:excess]

    pruned = 0
    for entry in to_delete:
        if entry.memory_id:
            await delete_memory(client, assistant_id, entry.memory_id)
            pruned += 1
    return pruned


async def search_memories(
    client: BackboardClient,
    assistant_id: str,
    query: str,
    limit: int = 10,
) -> list[MemoryEntry]:
    """Search memories by semantic similarity."""
    result = await client.post(
        f"/assistants/{assistant_id}/memories/search",
        json={"query": query, "limit": limit},
    )

    memories_raw = (
        result if isinstance(result, list) else result.get("memories", result.get("data", []))
    )
    return [parse_memory(m.get("content", str(m)), raw=m) for m in memories_raw]


async def list_memories(
    client: BackboardClient,
    assistant_id: str,
) -> list[MemoryEntry]:
    """List all memories for an assistant."""
    result = await client.get(f"/assistants/{assistant_id}/memories")
    memories_raw = (
        result if isinstance(result, list) else result.get("memories", result.get("data", []))
    )
    return [parse_memory(m.get("content", str(m)), raw=m) for m in memories_raw]


async def update_memory(
    client: BackboardClient,
    assistant_id: str,
    memory_id: str,
    content: str,
) -> dict[str, Any]:
    """Update a memory's content."""
    return await client.put(
        f"/assistants/{assistant_id}/memories/{memory_id}",
        json={"content": content},
    )


async def delete_memory(
    client: BackboardClient,
    assistant_id: str,
    memory_id: str,
) -> None:
    """Delete a memory."""
    await client.delete(f"/assistants/{assistant_id}/memories/{memory_id}")


async def clear_memories(
    client: BackboardClient,
    assistant_id: str,
) -> int:
    """Delete ALL memories for an assistant. Returns count deleted."""
    entries = await list_memories(client, assistant_id)
    deleted = 0
    for entry in entries:
        if entry.memory_id:
            await delete_memory(client, assistant_id, entry.memory_id)
            deleted += 1
    return deleted
