"""Shared test fixtures for TribalMind."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from tribalmind.backboard.client import BackboardClient
from tribalmind.config.settings import TribalSettings, clear_settings_cache


@pytest.fixture(autouse=True)
def _clear_settings():
    """Clear the settings cache before and after each test."""
    clear_settings_cache()
    yield
    clear_settings_cache()


@pytest.fixture
def settings(tmp_path, monkeypatch):
    """Create a TribalSettings with test defaults."""
    monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-api-key")
    monkeypatch.setenv("TRIBAL_PROJECT_ROOT", str(tmp_path))
    monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "test-assistant-123")
    return TribalSettings()


@pytest.fixture
def mock_backboard_client():
    """Create a mock BackboardClient."""
    client = AsyncMock(spec=BackboardClient)
    client.get = AsyncMock(return_value={})
    client.post = AsyncMock(return_value={})
    client.put = AsyncMock(return_value={})
    client.delete = AsyncMock(return_value={})
    client.__aenter__ = AsyncMock(return_value=client)
    client.__aexit__ = AsyncMock(return_value=None)
    return client
