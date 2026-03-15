"""Tests for the tribal init command."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tribalmind.cli.app import app
from typer.testing import CliRunner

runner = CliRunner()


class TestInitCommand:
    @patch("tribalmind.cli.init_cmd._setup_assistant", new_callable=AsyncMock)
    @patch("tribalmind.cli.init_cmd._find_git_root")
    @patch("tribalmind.config.credentials.get_backboard_api_key", return_value="test-key-12345678")
    def test_init_with_existing_key(self, mock_get_key, mock_git_root, mock_setup, tmp_path):
        mock_git_root.return_value = tmp_path
        mock_setup.return_value = {"assistant_id": "ast-123"}

        # Input: "1" for LLM selection (Anthropic), "n" for agent integration
        result = runner.invoke(app, ["init"], input="1\nn\n")
        assert result.exit_code == 0
        assert "initialized" in result.output.lower() or "ast-123" in result.output
        mock_setup.assert_called_once()

    @patch("tribalmind.cli.init_cmd._setup_assistant", new_callable=AsyncMock)
    @patch("tribalmind.cli.init_cmd._find_git_root")
    @patch("tribalmind.config.credentials.get_backboard_api_key", return_value=None)
    @patch("tribalmind.config.credentials.set_credential")
    def test_init_with_api_key_flag(
        self, mock_set, mock_get_key, mock_git_root, mock_setup, tmp_path,
    ):
        mock_git_root.return_value = tmp_path
        mock_setup.return_value = {"assistant_id": "ast-456"}

        result = runner.invoke(app, ["init", "--api-key", "sk-test1234567890"])
        assert result.exit_code == 0
        assert "ast-456" in result.output
        mock_set.assert_called_once()

    @patch("tribalmind.cli.init_cmd._setup_assistant", new_callable=AsyncMock)
    @patch("tribalmind.config.credentials.set_credential")
    def test_init_api_error(self, mock_set, mock_setup):
        from tribalmind.backboard.client import BackboardError
        mock_setup.side_effect = BackboardError(401, "Invalid API key")

        result = runner.invoke(app, ["init", "--api-key", "sk-bad-key-test"])
        assert result.exit_code == 1
        assert "401" in result.output

    @patch("tribalmind.cli.init_cmd._setup_assistant", new_callable=AsyncMock)
    @patch("tribalmind.cli.init_cmd._find_git_root")
    @patch("tribalmind.backboard.client.BackboardClient", autospec=True)
    @patch("tribalmind.config.credentials.get_backboard_api_key", return_value=None)
    @patch("tribalmind.config.credentials.set_credential")
    def test_init_prompts_for_key(
        self, mock_set, mock_get_key, mock_client_cls, mock_git_root,
        mock_setup, tmp_path,
    ):
        mock_git_root.return_value = tmp_path
        mock_setup.return_value = {"assistant_id": "ast-789"}
        # Make the validation client a no-op async context manager
        client_instance = AsyncMock()
        mock_client_cls.return_value = client_instance

        # Input: API key, "1" for LLM selection, "n" for agent integration
        result = runner.invoke(app, ["init"], input="my-secret-api-key-1234\n1\nn\n")
        assert result.exit_code == 0
        mock_set.assert_called_once()
