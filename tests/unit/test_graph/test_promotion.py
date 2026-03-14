"""Tests for the promotion node."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from tribalmind.backboard.client import BackboardError
from tribalmind.backboard.memory import MemoryEntry
from tribalmind.graph.promotion import (
    TRUST_INCREMENT,
    _find_existing_memory,
    _promote_to_org,
    _store_or_update_memory,
    promotion_node,
)
from tribalmind.graph.state import TribalState


def _make_state(**overrides) -> TribalState:
    """Build a minimal TribalState dict with sensible defaults."""
    base: TribalState = {
        "is_error": True,
        "error_signature": "ModuleNotFoundError: No module named 'foo'",
        "error_package": "foo",
        "error_type": "ModuleNotFoundError",
        "suggested_fix": "pip install foo",
        "fix_confidence": 0.9,
    }
    base.update(overrides)
    return base


class TestFindExistingMemory:
    @pytest.mark.asyncio
    async def test_returns_matching_sig(self, mock_backboard_client):
        entry = MemoryEntry(content="test", memory_id="mem-1", sig="abc123")
        with patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[entry]),
        ):
            result = await _find_existing_memory(
                mock_backboard_client, "asst-1", "abc123"
            )
        assert result is entry

    @pytest.mark.asyncio
    async def test_returns_none_for_different_sig(self, mock_backboard_client):
        entry = MemoryEntry(content="test", memory_id="mem-1", sig="other_sig")
        with patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[entry]),
        ):
            result = await _find_existing_memory(
                mock_backboard_client, "asst-1", "abc123"
            )
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_for_empty_results(self, mock_backboard_client):
        with patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[]),
        ):
            result = await _find_existing_memory(
                mock_backboard_client, "asst-1", "abc123"
            )
        assert result is None


class TestStoreOrUpdateMemory:
    @pytest.mark.asyncio
    async def test_creates_new_memory_when_none_exists(self, mock_backboard_client):
        mock_backboard_client.post = AsyncMock(
            return_value={"memory_id": "mem-new", "content": "..."}
        )
        with patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[]),
        ):
            mem_id, trust = await _store_or_update_memory(
                mock_backboard_client, "asst-1", _make_state()
            )
        assert mem_id == "mem-new"
        assert trust == TRUST_INCREMENT
        mock_backboard_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_updates_existing_memory_trust(self, mock_backboard_client):
        state = _make_state()
        existing = MemoryEntry(
            content="old",
            memory_id="mem-existing",
            category="error",
            package="foo",
            error_text="err",
            fix_text="pip install foo",
            trust_score=2.0,
            sig=state["error_signature"],
        )
        with patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[existing]),
        ):
            mem_id, trust = await _store_or_update_memory(
                mock_backboard_client, "asst-1", state
            )
        assert mem_id == "mem-existing"
        assert trust == 2.0 + TRUST_INCREMENT
        mock_backboard_client.put.assert_called_once()


class TestPromoteToOrg:
    @pytest.mark.asyncio
    async def test_promotes_when_not_in_org(self, mock_backboard_client):
        mock_backboard_client.post = AsyncMock(return_value={"memory_id": "org-mem-1"})
        with patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[]),
        ):
            result = await _promote_to_org(
                mock_backboard_client, "org-asst-1", _make_state(), 3.0
            )
        assert result is True
        mock_backboard_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_skips_when_already_in_org(self, mock_backboard_client):
        state = _make_state()
        existing = MemoryEntry(
            content="already there",
            memory_id="org-mem-1",
            sig=state["error_signature"],
        )
        with patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[existing]),
        ):
            result = await _promote_to_org(
                mock_backboard_client, "org-asst-1", state, 3.0
            )
        assert result is False


class TestPromotionNode:
    @pytest.mark.asyncio
    async def test_skips_when_no_fix(self):
        state = _make_state(suggested_fix=None)
        result = await promotion_node(state)
        assert result["promoted"] is False
        assert "no fix" in result["log"][0]

    @pytest.mark.asyncio
    async def test_skips_when_no_project_assistant(self, monkeypatch):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "")
        state = _make_state()
        result = await promotion_node(state)
        assert result["promoted"] is False
        assert "no project assistant" in result["log"][0]

    @pytest.mark.asyncio
    async def test_stores_memory_without_promotion(self, monkeypatch, mock_backboard_client):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")
        monkeypatch.setenv("TRIBAL_TEAM_SHARING_ENABLED", "false")

        mock_backboard_client.post = AsyncMock(return_value={"memory_id": "mem-1"})

        with patch(
            "tribalmind.graph.promotion.create_client",
            return_value=mock_backboard_client,
        ), patch(
            "tribalmind.graph.promotion.search_memories",
            AsyncMock(return_value=[]),
        ):
            result = await promotion_node(_make_state())

        assert result["promoted"] is False
        assert "mem-1" in result["log"][0]

    @pytest.mark.asyncio
    async def test_promotes_when_trust_exceeds_threshold(
        self, monkeypatch, mock_backboard_client
    ):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")
        monkeypatch.setenv("TRIBAL_ORG_ASSISTANT_ID", "asst-org")
        monkeypatch.setenv("TRIBAL_TEAM_SHARING_ENABLED", "true")
        monkeypatch.setenv("TRIBAL_TRUST_THRESHOLD", "2.0")

        # Existing memory with trust just below threshold after increment
        state = _make_state()
        existing = MemoryEntry(
            content="old",
            memory_id="mem-existing",
            category="error",
            package="foo",
            trust_score=1.5,
            sig=state["error_signature"],
        )
        # After increment: 1.5 + 1.0 = 2.5 >= 2.0 threshold

        call_count = 0

        async def mock_search(client, assistant_id, query, limit=10):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                # First call: project search finds existing
                return [existing]
            # Second call: org search finds nothing (not yet promoted)
            return []

        with patch(
            "tribalmind.graph.promotion.create_client",
            return_value=mock_backboard_client,
        ), patch(
            "tribalmind.graph.promotion.search_memories",
            side_effect=mock_search,
        ):
            mock_backboard_client.post = AsyncMock(return_value={"memory_id": "org-mem-1"})
            result = await promotion_node(state)

        assert result["promoted"] is True
        assert "promoted=True" in result["log"][0]

    @pytest.mark.asyncio
    async def test_handles_backboard_error(self, monkeypatch, mock_backboard_client):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")

        mock_backboard_client.__aenter__ = AsyncMock(
            side_effect=BackboardError(500, "Internal server error")
        )

        with patch(
            "tribalmind.graph.promotion.create_client",
            return_value=mock_backboard_client,
        ):
            result = await promotion_node(_make_state())

        assert result["promoted"] is False
        assert "error" in result["log"][0]
