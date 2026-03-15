"""Tests for the tribal forget command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from tribalmind.backboard.memory import MemoryEntry
from tribalmind.cli.app import app
from typer.testing import CliRunner

runner = CliRunner()


def _extract_json(output: str) -> dict:
    """Extract JSON from output that may have preamble text."""
    start = output.index("{")
    return json.loads(output[start:])


class TestForgetCommand:
    @patch("tribalmind.backboard.memory.delete_memory", new_callable=AsyncMock)
    @patch("tribalmind.backboard.client.create_client")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_by_id(self, mock_settings, mock_create_client, mock_delete):
        mock_settings.return_value.project_assistant_id = "ast-123"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_client

        result = runner.invoke(app, ["forget", "--id", "mem-001", "--yes"])
        assert result.exit_code == 0
        assert "Deleted" in result.output or "mem-001" in result.output

    @patch("tribalmind.backboard.memory.delete_memory", new_callable=AsyncMock)
    @patch("tribalmind.backboard.client.create_client")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_by_id_json(self, mock_settings, mock_create_client, mock_delete):
        mock_settings.return_value.project_assistant_id = "ast-123"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_client

        result = runner.invoke(app, ["forget", "--id", "mem-001", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["deleted"] == ["mem-001"]

    @patch("tribalmind.backboard.memory.clear_memories", new_callable=AsyncMock, return_value=5)
    @patch("tribalmind.backboard.client.create_client")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_all_with_yes(self, mock_settings, mock_create_client, mock_clear):
        mock_settings.return_value.project_assistant_id = "ast-123"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_client

        result = runner.invoke(app, ["forget", "--all", "--yes"])
        assert result.exit_code == 0
        assert "5" in result.output

    @patch("tribalmind.config.settings.get_settings")
    def test_forget_no_assistant(self, mock_settings):
        mock_settings.return_value.project_assistant_id = None

        result = runner.invoke(app, ["forget", "--id", "mem-001"])
        assert result.exit_code == 1
        assert "tribal init" in result.output

    def test_forget_no_args(self):
        result = runner.invoke(app, ["forget"])
        assert result.exit_code == 1

    @patch("tribalmind.backboard.memory.delete_memory", new_callable=AsyncMock)
    @patch("tribalmind.backboard.memory.search_memories", new_callable=AsyncMock)
    @patch("tribalmind.backboard.client.create_client")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_by_query_with_yes(
        self, mock_settings, mock_create_client, mock_search, mock_delete,
    ):
        mock_settings.return_value.project_assistant_id = "ast-123"

        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=None)
        mock_create_client.return_value = mock_client

        mock_search.return_value = [
            MemoryEntry(raw_content="test", memory_id="mem-001", category="fix", content="do X"),
        ]

        result = runner.invoke(app, ["forget", "--yes", "old", "redis", "fix"])
        assert result.exit_code == 0
        assert "1" in result.output
