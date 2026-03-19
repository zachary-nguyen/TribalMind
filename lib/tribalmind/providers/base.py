"""MemoryProvider protocol — the minimal interface all providers must implement."""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from tribalmind.backboard.memory import MemoryEntry


@runtime_checkable
class MemoryProvider(Protocol):
    """Async interface for memory storage backends.

    All providers must implement these methods. The MemoryEntry dataclass
    and JSON schema (category/subject/content) are TribalMind's layer,
    independent of the underlying storage.
    """

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Store a memory. Returns the raw provider response."""
        ...

    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        """Search memories by semantic similarity."""
        ...

    async def list_all(self) -> list[MemoryEntry]:
        """List all stored memories."""
        ...

    async def delete(self, memory_id: str) -> None:
        """Delete a single memory by ID."""
        ...

    async def update(self, memory_id: str, content: str) -> dict[str, Any]:
        """Update a memory's content. Returns the raw provider response."""
        ...

    async def clear(self) -> int:
        """Delete ALL memories. Returns the count deleted."""
        ...

    async def enforce_limit(self, max_memories: int) -> int:
        """Prune oldest memories if count exceeds max_memories. Returns count pruned."""
        ...

    async def close(self) -> None:
        """Release any resources held by the provider."""
        ...

    async def __aenter__(self) -> MemoryProvider:
        ...

    async def __aexit__(self, *args: Any) -> None:
        ...
