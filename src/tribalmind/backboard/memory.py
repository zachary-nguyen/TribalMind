"""Backboard memory management for storing and retrieving knowledge.

Memories are stored as content strings with structured metadata encoded inline:
  "[error] package=requests version=2.31 | ConnectionError: timeout | fix: increase timeout | confidence=0.85"

This encoding is necessary because Backboard memories are plain content strings.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

from tribalmind.backboard.client import BackboardClient


@dataclass
class MemoryEntry:
    """Parsed representation of a Backboard memory."""

    content: str
    memory_id: str = ""
    category: str = ""  # error, fix, context, upstream
    package: str = ""
    version: str = ""
    error_text: str = ""
    fix_text: str = ""
    confidence: float = 0.0
    trust_score: float = 0.0
    relevance_score: float = 0.0  # from search results
    raw: dict[str, Any] = field(default_factory=dict)


def encode_memory(
    category: str,
    *,
    package: str = "",
    version: str = "",
    error_text: str = "",
    fix_text: str = "",
    confidence: float = 0.0,
    trust_score: float = 0.0,
    extra: str = "",
) -> str:
    """Encode structured data into a Backboard memory content string."""
    parts = [f"[{category}]"]

    if package:
        parts.append(f"package={package}")
    if version:
        parts.append(f"version={version}")

    parts.append("|")

    if error_text:
        parts.append(error_text)
        parts.append("|")

    if fix_text:
        parts.append(f"fix: {fix_text}")
        parts.append("|")

    if confidence:
        parts.append(f"confidence={confidence:.2f}")
    if trust_score:
        parts.append(f"trust={trust_score:.2f}")

    if extra:
        parts.append(f"| {extra}")

    return " ".join(parts)


def parse_memory(content: str, raw: dict[str, Any] | None = None) -> MemoryEntry:
    """Parse a Backboard memory content string into a MemoryEntry."""
    entry = MemoryEntry(content=content, raw=raw or {})

    if raw:
        entry.memory_id = raw.get("id", raw.get("memory_id", ""))
        entry.relevance_score = raw.get("score", raw.get("relevance", 0.0))

    # Parse category tag
    cat_match = re.match(r"\[(\w+)\]", content)
    if cat_match:
        entry.category = cat_match.group(1)

    # Parse key=value pairs
    for match in re.finditer(r"(\w+)=([\w.\-]+)", content):
        key, val = match.group(1), match.group(2)
        if key == "package":
            entry.package = val
        elif key == "version":
            entry.version = val
        elif key == "confidence":
            entry.confidence = float(val)
        elif key == "trust":
            entry.trust_score = float(val)

    # Parse fix text
    fix_match = re.search(r"fix:\s*(.+?)(?:\s*\||$)", content)
    if fix_match:
        entry.fix_text = fix_match.group(1).strip()

    # Parse error text (between first | and second |)
    pipe_sections = content.split("|")
    if len(pipe_sections) >= 2:
        entry.error_text = pipe_sections[1].strip()

    return entry


async def add_memory(
    client: BackboardClient,
    assistant_id: str,
    content: str,
) -> dict[str, Any]:
    """Add a memory to a Backboard assistant."""
    return await client.post(
        f"/assistants/{assistant_id}/memories",
        json={"content": content},
    )


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

    memories_raw = result if isinstance(result, list) else result.get("memories", result.get("data", []))
    return [parse_memory(m.get("content", str(m)), raw=m) for m in memories_raw]


async def list_memories(
    client: BackboardClient,
    assistant_id: str,
) -> list[MemoryEntry]:
    """List all memories for an assistant."""
    result = await client.get(f"/assistants/{assistant_id}/memories")
    memories_raw = result if isinstance(result, list) else result.get("memories", result.get("data", []))
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
