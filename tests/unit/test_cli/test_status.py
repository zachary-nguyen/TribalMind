"""Tests for the tribal status command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from tribalmind.cli.app import app
from typer.testing import CliRunner

runner = CliRunner()


def _extract_json(output: str) -> dict:
    """Extract JSON from output that may have preamble text."""
    start = output.index("{")
    return json.loads(output[start:])


class TestStatusCommand:
    @patch("tribalmind.cli.status_cmd._get_memory_count", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_status_configured(self, mock_settings, mock_count):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.project_root = "/my/project"
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.model_name = "claude-sonnet-4-20250514"
        mock_count.return_value = 42

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "ast-123" in result.output
        assert "42" in result.output

    @patch("tribalmind.config.settings.get_settings")
    def test_status_not_configured(self, mock_settings):
        mock_settings.return_value.project_assistant_id = None
        mock_settings.return_value.project_root = "/my/project"
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.model_name = "claude-sonnet-4-20250514"

        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "not initialized" in result.output.lower()

    @patch("tribalmind.cli.status_cmd._get_memory_count", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_status_json(self, mock_settings, mock_count):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.project_root = "/my/project"
        mock_settings.return_value.llm_provider = "anthropic"
        mock_settings.return_value.model_name = "claude-sonnet-4-20250514"
        mock_count.return_value = 10

        result = runner.invoke(app, ["status", "--json"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["configured"] is True
        assert data["memory_count"] == 10
        assert data["assistant_id"] == "ast-123"
