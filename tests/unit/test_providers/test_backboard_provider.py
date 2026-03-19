"""Tests for BackboardProvider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock

import pytest
from tribalmind.backboard.memory import MemoryEntry
from tribalmind.providers.backboard_provider import BackboardProvider


@pytest.fixture
def mock_client():
    client = AsyncMock()
    client.post = AsyncMock(return_value={})
    client.get = AsyncMock(return_value=[])
    client.put = AsyncMock(return_value={})
    client.delete = AsyncMock(return_value={})
    client.close = AsyncMock()
    return client


@pytest.fixture
def provider(mock_client):
    return BackboardProvider(client=mock_client, assistant_id="test-assistant-123")


class TestBackboardProviderAdd:
    async def test_add_calls_backboard(self, provider, mock_client):
        content = json.dumps({"category": "fix", "subject": "test", "content": "test content"})
        await provider.add(content)
        mock_client.post.assert_called_once()
        call_args = mock_client.post.call_args
        assert "test-assistant-123" in call_args[0][0]
        assert "memories" in call_args[0][0]

    async def test_add_with_metadata(self, provider, mock_client):
        metadata = {"category": "fix", "subject": "test"}
        await provider.add("content", metadata=metadata)
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["json"]["metadata"] == metadata


class TestBackboardProviderSearch:
    async def test_search_returns_memory_entries(self, provider, mock_client):
        mock_client.post.return_value = [
            {
                "id": "mem-1",
                "content": json.dumps({
                    "category": "fix",
                    "subject": "test",
                    "content": "test content",
                }),
                "score": 0.1,
            }
        ]
        results = await provider.search("test query")
        assert len(results) == 1
        assert isinstance(results[0], MemoryEntry)
        assert results[0].category == "fix"

    async def test_search_with_limit(self, provider, mock_client):
        mock_client.post.return_value = []
        await provider.search("test", limit=5)
        call_kwargs = mock_client.post.call_args[1]
        assert call_kwargs["json"]["limit"] == 5


class TestBackboardProviderListAll:
    async def test_list_all_returns_entries(self, provider, mock_client):
        mock_client.get.return_value = [
            {
                "id": "mem-1",
                "content": json.dumps({
                    "category": "tip",
                    "subject": "debug",
                    "content": "use verbose",
                }),
            }
        ]
        results = await provider.list_all()
        assert len(results) == 1
        assert results[0].category == "tip"


class TestBackboardProviderDelete:
    async def test_delete_calls_backboard(self, provider, mock_client):
        await provider.delete("mem-123")
        mock_client.delete.assert_called_once()
        assert "mem-123" in mock_client.delete.call_args[0][0]


class TestBackboardProviderUpdate:
    async def test_update_calls_backboard(self, provider, mock_client):
        await provider.update("mem-123", "new content")
        mock_client.put.assert_called_once()
        assert "mem-123" in mock_client.put.call_args[0][0]


class TestBackboardProviderClear:
    async def test_clear_deletes_all(self, provider, mock_client):
        mock_client.get.return_value = [
            {"id": "mem-1", "content": "{}"},
            {"id": "mem-2", "content": "{}"},
        ]
        count = await provider.clear()
        assert count == 2
        assert mock_client.delete.call_count == 2


class TestBackboardProviderEnforceLimit:
    async def test_enforce_limit_prunes_excess(self, provider, mock_client):
        mock_client.get.return_value = [
            {"id": f"mem-{i}", "content": "{}", "created_at": f"2024-01-0{i}"}
            for i in range(1, 6)
        ]
        pruned = await provider.enforce_limit(3)
        assert pruned == 2
        assert mock_client.delete.call_count == 2

    async def test_enforce_limit_no_op_when_under(self, provider, mock_client):
        mock_client.get.return_value = [
            {"id": "mem-1", "content": "{}"},
        ]
        pruned = await provider.enforce_limit(10)
        assert pruned == 0
        mock_client.delete.assert_not_called()


class TestBackboardProviderContextManager:
    async def test_context_manager(self, mock_client):
        provider = BackboardProvider(client=mock_client, assistant_id="test")
        async with provider:
            pass
        # Client was passed in, so provider doesn't own it — shouldn't close
        mock_client.close.assert_not_called()

    async def test_context_manager_owns_client(self, monkeypatch):
        """When no client is passed, provider creates and closes its own."""
        mock_client = AsyncMock()

        def mock_create():
            return mock_client

        monkeypatch.setattr(
            "tribalmind.providers.backboard_provider.create_client",
            mock_create,
        )
        provider = BackboardProvider(assistant_id="test")
        async with provider:
            pass
        mock_client.close.assert_called_once()
