"""Mem0 memory provider — uses the mem0ai SDK for memory storage.

Mem0 offers graph memory and its own extraction pipeline.

Docs: https://docs.mem0.ai/introduction
"""

from __future__ import annotations

import logging
from typing import Any

from mem0 import MemoryClient

from tribalmind.backboard.memory import MemoryEntry, parse_memory

logger = logging.getLogger(__name__)


class Mem0Provider:
    """Memory provider backed by Mem0's managed API.

    Maps TribalMind operations to the Mem0 SDK:
    - add → client.add(messages, user_id=...)
    - search → client.search(query, user_id=..., top_k=...)
    - list_all → client.get_all(user_id=...)
    - delete → client.delete(memory_id)
    - update → client.update(memory_id, text=...)
    """

    def __init__(
        self,
        api_key: str,
        *,
        org_id: str | None = None,
        project_id: str | None = None,
        user_id: str = "tribalmind",
    ):
        # org_id and project_id are passed to the constructor;
        # the SDK attaches them to every request via _prepare_params.
        self._client = MemoryClient(
            api_key=api_key,
            org_id=org_id,
            project_id=project_id,
        )
        self._user_id = user_id

    def _mem0_to_entry(self, item: dict[str, Any]) -> MemoryEntry:
        """Convert a Mem0 result dict to a MemoryEntry."""
        # Mem0 stores the memory text in 'memory' field
        raw_content = item.get("memory", "")

        # Try to parse as our structured JSON format
        entry = parse_memory(raw_content, raw=item)

        # Override memory_id from Mem0's id field
        entry.memory_id = item.get("id", "")

        # Mem0 search returns a 'score' field (higher = more relevant)
        if "score" in item:
            entry.relevance_score = item["score"]

        return entry

    def _extract_results(self, response: Any) -> list[dict[str, Any]]:
        """Extract the list of memory items from a Mem0 SDK response."""
        if isinstance(response, dict):
            return response.get("results", response.get("memories", []))
        if isinstance(response, list):
            return response
        return []

    async def add(self, content: str, metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        kwargs: dict[str, Any] = {"user_id": self._user_id}
        if metadata:
            kwargs["metadata"] = metadata
        result = self._client.add(content, **kwargs)
        return result if isinstance(result, dict) else {"result": result}

    @property
    def _user_filters(self) -> dict[str, str]:
        """Mem0 v2 API requires user_id inside a 'filters' dict for queries."""
        return {"user_id": self._user_id}

    async def search(self, query: str, limit: int = 10) -> list[MemoryEntry]:
        results = self._client.search(
            query, filters=self._user_filters, top_k=limit,
        )
        items = self._extract_results(results)
        return [self._mem0_to_entry(item) for item in items]

    async def list_all(self) -> list[MemoryEntry]:
        results = self._client.get_all(filters=self._user_filters)
        items = self._extract_results(results)
        return [self._mem0_to_entry(item) for item in items]

    async def delete(self, memory_id: str) -> None:
        self._client.delete(memory_id)

    async def update(self, memory_id: str, content: str) -> dict[str, Any]:
        # Mem0 SDK uses 'text=' keyword, not positional
        result = self._client.update(memory_id, text=content)
        return result if isinstance(result, dict) else {"result": result}

    async def clear(self) -> int:
        entries = await self.list_all()
        deleted = 0
        for entry in entries:
            if entry.memory_id:
                await self.delete(entry.memory_id)
                deleted += 1
        return deleted

    async def enforce_limit(self, max_memories: int) -> int:
        if max_memories <= 0:
            return 0

        entries = await self.list_all()
        excess = len(entries) - max_memories
        if excess <= 0:
            return 0

        # Sort by created_at ascending so oldest come first
        entries.sort(key=lambda e: e.raw.get("created_at", ""))
        to_delete = entries[:excess]

        pruned = 0
        for entry in to_delete:
            if entry.memory_id:
                await self.delete(entry.memory_id)
                pruned += 1
        return pruned

    async def close(self) -> None:
        pass

    async def __aenter__(self) -> Mem0Provider:
        return self

    async def __aexit__(self, *args: Any) -> None:
        await self.close()
