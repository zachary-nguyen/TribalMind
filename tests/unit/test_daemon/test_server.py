"""Tests for the daemon server's fix validation and user-fix learning logic."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from tribalmind.daemon.server import TribalDaemon, _LastError, _PendingFix
from tribalmind.graph.state import ShellEvent


class TestPendingFix:
    def test_stores_fields(self):
        pf = _PendingFix(
            memory_id="mem-1",
            error_signature="sig-abc",
            cwd="/project",
            timestamp=1000.0,
        )
        assert pf.memory_id == "mem-1"
        assert pf.error_signature == "sig-abc"
        assert pf.cwd == "/project"
        assert pf.timestamp == 1000.0


class TestFixValidation:
    def _make_daemon(self) -> TribalDaemon:
        """Create a daemon without starting the server."""
        daemon = object.__new__(TribalDaemon)
        daemon._settings = None
        daemon._server = None
        daemon._graph = None
        daemon._pending_fix = None
        daemon._last_error = None
        return daemon

    def _make_event(self, exit_code=0, cwd="/project", timestamp=1010.0) -> ShellEvent:
        return ShellEvent(
            command="python main.py",
            exit_code=exit_code,
            cwd=cwd,
            timestamp=timestamp,
        )

    @pytest.mark.asyncio
    async def test_clears_pending_on_different_cwd(self):
        daemon = self._make_daemon()
        daemon._pending_fix = _PendingFix("mem-1", "sig", "/project", 1000.0)

        event = self._make_event(cwd="/other-project")
        await daemon._validate_fix(event)

        assert daemon._pending_fix is None

    @pytest.mark.asyncio
    async def test_clears_pending_on_timeout(self):
        daemon = self._make_daemon()
        daemon._pending_fix = _PendingFix("mem-1", "sig", "/project", 1000.0)

        event = self._make_event(timestamp=2000.0)  # 1000s > 300s timeout
        await daemon._validate_fix(event)

        assert daemon._pending_fix is None

    @pytest.mark.asyncio
    async def test_no_crash_when_no_pending(self):
        daemon = self._make_daemon()
        event = self._make_event()
        await daemon._validate_fix(event)
        # Should not raise

    @pytest.mark.asyncio
    async def test_consumes_pending_on_valid_fix(self, monkeypatch, mock_backboard_client):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")

        daemon = self._make_daemon()
        daemon._pending_fix = _PendingFix("mem-1", "sig", "/project", 1000.0)

        mock_backboard_client.get = lambda *a, **kw: _async_return({
            "memory_id": "mem-1",
            "content": "[error] package=foo | err"
            " | fix: pip install foo | confidence=0.60 trust=1.00",
        })
        mock_backboard_client.put = lambda *a, **kw: _async_return({})

        from unittest.mock import patch
        with patch(
            "tribalmind.backboard.client.create_client",
            return_value=mock_backboard_client,
        ):
            event = self._make_event(cwd="/project", timestamp=1010.0)
            await daemon._validate_fix(event)

        assert daemon._pending_fix is None


class TestUserFixLearning:
    def _make_daemon(self) -> TribalDaemon:
        daemon = object.__new__(TribalDaemon)
        daemon._settings = None
        daemon._server = None
        daemon._graph = None
        daemon._pending_fix = None
        daemon._last_error = None
        return daemon

    def _make_last_error(self, cwd="/project", timestamp=1000.0) -> _LastError:
        return _LastError(
            error_signature="ModuleNotFoundError: No module named 'foo'",
            error_type="ModuleNotFoundError",
            error_package="foo",
            cwd=cwd,
            timestamp=timestamp,
        )

    def _make_event(self, command="pip install foo", exit_code=0,
                    cwd="/project", timestamp=1010.0) -> ShellEvent:
        return ShellEvent(
            command=command,
            exit_code=exit_code,
            cwd=cwd,
            timestamp=timestamp,
        )

    @pytest.mark.asyncio
    async def test_stores_user_fix(self, monkeypatch, mock_backboard_client):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")

        daemon = self._make_daemon()
        daemon._last_error = self._make_last_error()

        mock_backboard_client.post = AsyncMock(
            return_value={"memory_id": "mem-user-1"}
        )

        with patch(
            "tribalmind.backboard.client.create_client",
            return_value=mock_backboard_client,
        ), patch(
            "tribalmind.backboard.memory.search_memories",
            AsyncMock(return_value=[]),
        ):
            await daemon._learn_user_fix(self._make_event())

        assert daemon._last_error is None
        mock_backboard_client.post.assert_called_once()

    @pytest.mark.asyncio
    async def test_clears_last_error_on_different_cwd(self):
        daemon = self._make_daemon()
        daemon._last_error = self._make_last_error(cwd="/project")

        await daemon._learn_user_fix(self._make_event(cwd="/other"))

        assert daemon._last_error is None

    @pytest.mark.asyncio
    async def test_clears_last_error_on_timeout(self):
        daemon = self._make_daemon()
        daemon._last_error = self._make_last_error(timestamp=1000.0)

        await daemon._learn_user_fix(self._make_event(timestamp=2000.0))

        assert daemon._last_error is None

    @pytest.mark.asyncio
    async def test_skips_trivial_commands(self):
        daemon = self._make_daemon()

        for cmd in ["ls", "cd ..", "pwd", "clear", "echo hello", "cat file.txt"]:
            daemon._last_error = self._make_last_error()
            await daemon._learn_user_fix(self._make_event(command=cmd))
            # _last_error consumed but no API call should happen
            assert daemon._last_error is None

    @pytest.mark.asyncio
    async def test_skips_when_memory_already_exists(self, monkeypatch, mock_backboard_client):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")

        from tribalmind.backboard.memory import MemoryEntry

        existing = MemoryEntry(
            content="existing fix",
            memory_id="mem-existing",
            fix_text="pip install foo",
            relevance_score=0.95,
        )

        daemon = self._make_daemon()
        daemon._last_error = self._make_last_error()

        mock_backboard_client.post = AsyncMock()

        with patch(
            "tribalmind.backboard.client.create_client",
            return_value=mock_backboard_client,
        ), patch(
            "tribalmind.backboard.memory.search_memories",
            AsyncMock(return_value=[existing]),
        ):
            await daemon._learn_user_fix(self._make_event())

        mock_backboard_client.post.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_crash_when_no_last_error(self):
        daemon = self._make_daemon()
        await daemon._learn_user_fix(self._make_event())
        # Should not raise

    @pytest.mark.asyncio
    async def test_no_crash_when_no_project_assistant(self, monkeypatch):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "")

        daemon = self._make_daemon()
        daemon._last_error = self._make_last_error()

        await daemon._learn_user_fix(self._make_event())
        assert daemon._last_error is None


async def _async_return(val):
    return val
