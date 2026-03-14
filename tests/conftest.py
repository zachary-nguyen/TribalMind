"""Shared test fixtures for TribalMind."""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from tribalmind.backboard.client import BackboardClient
from tribalmind.config.settings import TribalSettings, clear_settings_cache
from tribalmind.graph.state import ShellEvent


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


@pytest.fixture
def shell_event_success():
    """A successful shell command event."""
    return ShellEvent(
        command="python -m pytest",
        exit_code=0,
        cwd="/home/user/project",
        timestamp=1710000000.0,
        shell="bash",
    )


@pytest.fixture
def shell_event_python_error():
    """A shell event with a Python traceback."""
    return ShellEvent(
        command="python main.py",
        exit_code=1,
        cwd="/home/user/project",
        timestamp=1710000000.0,
        stderr=(
            "Traceback (most recent call last):\n"
            '  File "main.py", line 5, in <module>\n'
            "    import nonexistent_module\n"
            "ModuleNotFoundError: No module named 'nonexistent_module'\n"
        ),
        shell="bash",
    )


@pytest.fixture
def shell_event_npm_error():
    """A shell event with an npm error."""
    return ShellEvent(
        command="npm install",
        exit_code=1,
        cwd="/home/user/project",
        timestamp=1710000000.0,
        stderr="npm ERR! 404 Not Found - GET https://registry.npmjs.org/fake-package\n",
        shell="bash",
    )
