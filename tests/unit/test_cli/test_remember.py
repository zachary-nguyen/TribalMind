"""Tests for the tribal remember command."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

from tribalmind.cli.app import app
from tribalmind.cli.remember_cmd import _PARSE_PROMPT, _parse_llm_response
from typer.testing import CliRunner

runner = CliRunner()


class TestParseLlmResponse:
    def test_valid_json(self):
        result = _parse_llm_response('{"category": "fix", "content": "pip install foo"}')
        assert result == {"category": "fix", "content": "pip install foo"}

    def test_json_in_markdown_fence(self):
        content = '```json\n{"category": "tip", "content": "use --verbose"}\n```'
        result = _parse_llm_response(content)
        assert result["category"] == "tip"
        assert result["content"] == "use --verbose"

    def test_empty_string(self):
        assert _parse_llm_response("") is None

    def test_invalid_json(self):
        assert _parse_llm_response("not json at all") is None


class TestRememberCommand:
    @patch("tribalmind.cli.remember_cmd._store_memory", new_callable=AsyncMock)
    def test_remember_with_text_arg(self, mock_store):
        mock_store.return_value = {
            "category": "fix",
            "subject": "numpy",
            "content": "pin to <1.26",
        }
        result = runner.invoke(app, ["remember", "numpy 1.26 breaks on 3.13"])
        assert result.exit_code == 0
        assert "Remembered" in result.output
        assert "numpy" in result.output
        mock_store.assert_called_once()

    @patch("tribalmind.cli.remember_cmd._store_memory", new_callable=AsyncMock)
    def test_remember_multiword_arg(self, mock_store):
        mock_store.return_value = {
            "category": "tip",
            "subject": "",
            "content": "always run migrations first",
        }
        result = runner.invoke(app, ["remember", "always", "run", "migrations", "first"])
        assert result.exit_code == 0
        mock_store.assert_called_once()
        # Arguments should be joined
        call_text = mock_store.call_args[0][0]
        assert "always run migrations first" == call_text

    def test_remember_no_input_no_stdin(self):
        result = runner.invoke(app, ["remember"])
        assert result.exit_code == 1
        # Typer runner provides empty stdin, so we hit "Empty input"
        assert "Empty input" in result.output or "No input" in result.output

    @patch("tribalmind.cli.remember_cmd._store_memory", new_callable=AsyncMock)
    def test_remember_stdin(self, mock_store):
        mock_store.return_value = {
            "category": "tip",
            "subject": "react",
            "content": "use --legacy-peer-deps",
        }
        result = runner.invoke(app, ["remember"], input="use --legacy-peer-deps for React 18\n")
        assert result.exit_code == 0
        assert "Remembered" in result.output


class TestParsePrompt:
    def test_prompt_has_schema_placeholder(self):
        assert "{schema}" in _PARSE_PROMPT

    def test_prompt_has_text_placeholder(self):
        filled = _PARSE_PROMPT.format(text="test input", schema="{}")
        assert "test input" in filled

    def test_prompt_documents_categories(self):
        assert "fix" in _PARSE_PROMPT
        assert "convention" in _PARSE_PROMPT
        assert "architecture" in _PARSE_PROMPT
        assert "context" in _PARSE_PROMPT
        assert "decision" in _PARSE_PROMPT
        assert "tip" in _PARSE_PROMPT
