"""Tests for the tribal recall command."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

from tribalmind.backboard.memory import MemoryEntry
from tribalmind.cli.app import app
from typer.testing import CliRunner

runner = CliRunner()


def _make_memory(**kwargs) -> MemoryEntry:
    defaults = {
        "raw_content": json.dumps({
            "category": "fix", "subject": "numpy",
            "content": "pin <1.26 for Python 3.13",
        }),
        "memory_id": "mem-001",
        "category": "fix",
        "subject": "numpy",
        "content": "pin <1.26 for Python 3.13",
        "relevance_score": 0.85,
    }
    defaults.update(kwargs)
    return MemoryEntry(**defaults)


def _extract_json(output: str) -> dict:
    """Extract JSON from output that may have preamble text (e.g. upgrade notice)."""
    start = output.index("{")
    return json.loads(output[start:])


class TestRecallCommand:
    @patch("tribalmind.cli.recall_cmd._search", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_recall_basic(self, mock_settings, mock_search):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search.return_value = [_make_memory()]

        result = runner.invoke(app, ["recall", "numpy"])
        assert result.exit_code == 0
        assert "numpy" in result.output
        assert "1 result" in result.output

    @patch("tribalmind.cli.recall_cmd._search", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_recall_json_output(self, mock_settings, mock_search):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search.return_value = [_make_memory()]

        result = runner.invoke(app, ["recall", "--json", "numpy"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["count"] == 1
        assert data["results"][0]["subject"] == "numpy"
        assert data["results"][0]["content"] == "pin <1.26 for Python 3.13"

    @patch("tribalmind.cli.recall_cmd._search", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_recall_no_results(self, mock_settings, mock_search):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search.return_value = []

        result = runner.invoke(app, ["recall", "nonexistent"])
        assert result.exit_code == 0
        assert "No memories found" in result.output

    @patch("tribalmind.config.settings.get_settings")
    def test_recall_no_assistant(self, mock_settings):
        mock_settings.return_value.project_assistant_id = None

        result = runner.invoke(app, ["recall", "query"])
        assert result.exit_code == 1
        assert "tribal init" in result.output

    def test_recall_no_query(self):
        result = runner.invoke(app, ["recall"])
        assert result.exit_code == 1

    @patch("tribalmind.cli.recall_cmd._search", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_recall_stdin(self, mock_settings, mock_search):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search.return_value = [_make_memory()]

        result = runner.invoke(app, ["recall"], input="numpy compatibility\n")
        assert result.exit_code == 0


class TestRecallCategoryFilter:
    """Tests for --category / -c filtering."""

    @patch("tribalmind.cli.recall_cmd._search", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_category_filters_results(self, mock_settings, mock_search):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search.return_value = [
            _make_memory(category="fix", subject="numpy"),
            _make_memory(category="convention", subject="imports"),
        ]

        result = runner.invoke(app, ["recall", "--category", "fix", "query"])
        assert result.exit_code == 0
        assert "numpy" in result.output
        assert "imports" not in result.output

    @patch("tribalmind.cli.recall_cmd._search", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_category_comma_separated(self, mock_settings, mock_search):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search.return_value = [
            _make_memory(category="fix", subject="numpy"),
            _make_memory(category="decision", subject="db choice"),
            _make_memory(category="tip", subject="perf hint"),
        ]

        result = runner.invoke(
            app, ["recall", "--category", "fix,decision", "query"],
        )
        assert result.exit_code == 0
        assert "numpy" in result.output
        assert "db choice" in result.output
        assert "perf hint" not in result.output

    @patch("tribalmind.cli.recall_cmd._search", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_category_json_output(self, mock_settings, mock_search):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search.return_value = [
            _make_memory(category="fix", subject="numpy"),
            _make_memory(category="tip", subject="perf"),
        ]

        result = runner.invoke(
            app, ["recall", "--json", "--category", "fix", "query"],
        )
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["count"] == 1
        assert data["results"][0]["category"] == "fix"

    def test_category_invalid_value(self):
        result = runner.invoke(
            app, ["recall", "--category", "bogus", "query"],
        )
        assert result.exit_code == 1
        assert "Invalid category" in result.output

    @patch("tribalmind.cli.recall_cmd._list_all", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_category_with_list(self, mock_settings, mock_list):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_list.return_value = [
            _make_memory(category="fix", subject="numpy"),
            _make_memory(category="convention", subject="imports"),
        ]

        result = runner.invoke(
            app, ["recall", "--list", "--category", "convention"],
        )
        assert result.exit_code == 0
        assert "imports" in result.output
        assert "numpy" not in result.output


class TestRecallAllProjectColumn:
    """Tests for --all showing project name in results (issue #21)."""

    @patch("tribalmind.cli.recall_cmd._search_all_assistants", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_all_json_has_project_field(self, mock_settings, mock_search_all):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search_all.return_value = [
            ("api-service", [_make_memory(subject="httpx timeout", relevance_score=0.91)]),
            ("mobile-app", [_make_memory(subject="async calls", relevance_score=0.87)]),
        ]

        result = runner.invoke(app, ["recall", "--all", "--json", "timeout"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["scope"] == "all"
        assert data["count"] == 2
        # Results should be sorted by relevance descending
        assert data["results"][0]["project"] == "api-service"
        assert data["results"][0]["relevance"] == 0.91
        assert data["results"][1]["project"] == "mobile-app"
        assert data["results"][1]["relevance"] == 0.87

    @patch("tribalmind.cli.recall_cmd._search_all_assistants", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_all_table_shows_project_column(self, mock_settings, mock_search_all):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search_all.return_value = [
            ("api-service", [_make_memory(subject="httpx timeout", relevance_score=0.91)]),
            ("TribalMind", [_make_memory(subject="backboard", relevance_score=0.83)]),
        ]

        result = runner.invoke(app, ["recall", "--all", "timeout"])
        assert result.exit_code == 0
        assert "api-service" in result.output
        assert "TribalMind" in result.output
        assert "Project" in result.output
        assert "2 result(s) across 2 repo(s)" in result.output

    @patch("tribalmind.cli.recall_cmd._search_all_assistants", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_all_results_sorted_by_relevance(self, mock_settings, mock_search_all):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search_all.return_value = [
            ("low-repo", [_make_memory(subject="low", relevance_score=0.50)]),
            ("high-repo", [_make_memory(subject="high", relevance_score=0.95)]),
        ]

        result = runner.invoke(app, ["recall", "--all", "--json", "query"])
        assert result.exit_code == 0
        data = _extract_json(result.output)
        assert data["results"][0]["project"] == "high-repo"
        assert data["results"][1]["project"] == "low-repo"

    @patch("tribalmind.cli.recall_cmd._search_all_assistants", new_callable=AsyncMock)
    @patch("tribalmind.config.settings.get_settings")
    def test_all_no_results(self, mock_settings, mock_search_all):
        mock_settings.return_value.project_assistant_id = "ast-123"
        mock_settings.return_value.org_assistant_id = None
        mock_search_all.return_value = []

        result = runner.invoke(app, ["recall", "--all", "nonexistent"])
        assert result.exit_code == 0
        assert "No memories found" in result.output
