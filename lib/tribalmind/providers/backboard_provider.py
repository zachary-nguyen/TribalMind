"""Backboard memory provider — wraps the existing Backboard API client.

This is the default provider and preserves 100% backward compatibility.
"""

from __future__ import annotations

from typing import Any

from tribalmind.backboard.client import BackboardClient, create_client
from tribalmind.backboard.memory import (
    MemoryEntry,
    add_memory,
    clear_memories,
    delete_memory,
    enforce_memory_limit,
    list_memories,
    search_memories,
    update_memory,
)


class BackboardProvider:
    """Memory provider backed by the Backboard API."""

    def __init__(self, client: BackboardClient | None = None, assistant_id: str = ""):
        self._client = client
        self._owns_client = client is None
        self._assistant_id = assistant_id

    def _get_assistant_id(self) -> str:
        if self._assistant_id:
            return self._assistant_id
        from tribalmind.config.settings import get_settings

        settings = get_settings()
        aid = settings.project_assistant_id
        if not aid:
            raise RuntimeError(
                "No project assistant configured. Run 'tribal init' first."
            )
        return aid

    async def _ensure_client(self) -> BackboardClient:
        if self._client is None:
            self._client = create_client()
        return self._client

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        client = await self._ensure_client()
        return await add_memory(client, self._get_assistant_id(), content, metadata=metadata)

    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        client = await self._ensure_client()
        return await search_memories(client, self._get_assistant_id(), query, limit=limit)

    async def list_all(self) -> list[MemoryEntry]:
        client = await self._ensure_client()
        return await list_memories(client, self._get_assistant_id())

    async def delete(self, memory_id: str) -> None:
        client = await self._ensure_client()
        await delete_memory(client, self._get_assistant_id(), memory_id)

    async def update(self, memory_id: str, content: str) -> dict[str, Any]:
        client = await self._ensure_client()
        return await update_memory(client, self._get_assistant_id(), memory_id, content)

    async def clear(self) -> int:
        client = await self._ensure_client()
        return await clear_memories(client, self._get_assistant_id())

    async def enforce_limit(self, max_memories: int) -> int:
        client = await self._ensure_client()
        return await enforce_memory_limit(client, self._get_assistant_id(), max_memories)

    async def close(self) -> None:
        if self._client and self._owns_client:
            await self._client.close()
            self._client = None

    async def __aenter__(self) -> BackboardProvider:
        await self._ensure_client()
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
