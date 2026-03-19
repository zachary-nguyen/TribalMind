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


def _mock_provider():
    """Create a mock provider with async context manager support."""
    provider = AsyncMock()
    provider.__aenter__ = AsyncMock(return_value=provider)
    provider.__aexit__ = AsyncMock(return_value=None)
    return provider


class TestForgetCommand:
    @patch("tribalmind.cli.forget_cmd.get_provider")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_by_id(self, mock_settings, mock_get_provider):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_get_provider.return_value = _mock_provider()

        result = runner.invoke(app, ["forget", "--id", "mem-001", "--yes"])
        assert result.exit_code == 0
        assert "Deleted" in result.output or "mem-001" in result.output

    @patch("tribalmind.cli.forget_cmd.get_provider")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_by_id_json(self, mock_settings, mock_get_provider):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_get_provider.return_value = _mock_provider()

        result = runner.invoke(app, ["forget", "--id", "mem-001", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["deleted"] == ["mem-001"]

    @patch("tribalmind.cli.forget_cmd.get_provider")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_all_with_yes(self, mock_settings, mock_get_provider):
        mock_settings.return_value.project_assistant_id = "ast-123"
        provider = _mock_provider()
        provider.clear.return_value = 5
        mock_get_provider.return_value = provider

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

    @patch("tribalmind.cli.forget_cmd.get_provider")
    @patch("tribalmind.config.settings.get_settings")
    def test_forget_by_query_with_yes(self, mock_settings, mock_get_provider):
        mock_settings.return_value.project_assistant_id = "ast-123"
        provider = _mock_provider()
        provider.search.return_value = [
            MemoryEntry(raw_content="test", memory_id="mem-001", category="fix", content="do X"),
        ]
        mock_get_provider.return_value = provider

        result = runner.invoke(app, ["forget", "--yes", "old", "redis", "fix"])
        assert result.exit_code == 0
        assert "1" in result.output
