"""Tests for the UI node."""

from __future__ import annotations

import pytest
from tribalmind.backboard.memory import MemoryEntry
from tribalmind.graph.state import ContextResult, TribalState
from tribalmind.graph.ui import (
    _confidence_label,
    _determine_source,
    render_insight_panel,
    ui_node,
)


def _make_state(**overrides) -> TribalState:
    """Build a minimal TribalState dict with sensible defaults."""
    base: TribalState = {
        "is_error": True,
        "error_signature": "ModuleNotFoundError: No module named 'foo'",
        "error_package": "foo",
        "error_type": "ModuleNotFoundError",
        "suggested_fix": "pip install foo",
        "fix_confidence": 0.85,
        "context": ContextResult(
            local_matches=[
                MemoryEntry(content="test", fix_text="pip install foo")
            ],
        ),
        "promoted": False,
    }
    base.update(overrides)
    return base


class TestConfidenceLabel:
    def test_high_confidence(self):
        label = _confidence_label(0.9)
        assert "90%" in label.plain
        assert "high" in label.plain

    def test_medium_confidence(self):
        label = _confidence_label(0.6)
        assert "60%" in label.plain
        assert "medium" in label.plain

    def test_low_confidence(self):
        label = _confidence_label(0.2)
        assert "20%" in label.plain
        assert "low" in label.plain


class TestDetermineSource:
    def test_local_history(self):
        ctx = ContextResult(
            local_matches=[MemoryEntry(content="x", fix_text="fix")]
        )
        assert _determine_source(ctx) == "local history"

    def test_team_knowledge(self):
        ctx = ContextResult(
            team_matches=[MemoryEntry(content="x", fix_text="fix")]
        )
        assert _determine_source(ctx) == "team knowledge"

    def test_upstream(self):
        ctx = ContextResult(upstream_info={"issues": []})
        assert _determine_source(ctx) == "upstream (GitHub)"

    def test_inference_fallback(self):
        ctx = ContextResult()
        assert _determine_source(ctx) == "inference"

    def test_none_context(self):
        assert _determine_source(None) == "unknown"


class TestRenderInsightPanel:
    def test_contains_error_type(self):
        rendered = render_insight_panel(_make_state())
        assert "ModuleNotFoundError" in rendered

    def test_contains_package(self):
        rendered = render_insight_panel(_make_state())
        assert "foo" in rendered

    def test_contains_fix(self):
        rendered = render_insight_panel(_make_state())
        assert "pip install foo" in rendered

    def test_contains_title(self):
        rendered = render_insight_panel(_make_state())
        assert "TribalMind Insight" in rendered

    def test_shows_promoted(self):
        rendered = render_insight_panel(_make_state(promoted=True))
        assert "promoted to team" in rendered

    def test_no_package_still_renders(self):
        rendered = render_insight_panel(_make_state(error_package=None))
        assert "ModuleNotFoundError" in rendered


class TestUiNode:
    @pytest.mark.asyncio
    async def test_displays_when_fix_present(self):
        result = await ui_node(_make_state())
        assert result["displayed"] is True

    @pytest.mark.asyncio
    async def test_skips_when_no_fix_and_no_context(self):
        state = _make_state(suggested_fix=None, context=None)
        result = await ui_node(state)
        assert result["displayed"] is False

    @pytest.mark.asyncio
    async def test_skips_when_low_confidence_no_context(self):
        state = _make_state(suggested_fix="try x", fix_confidence=0.1, context=None)
        result = await ui_node(state)
        assert result["displayed"] is False

    @pytest.mark.asyncio
    async def test_displays_context_matches_without_fix(self):
        ctx = ContextResult(
            local_matches=[MemoryEntry(content="related error info")]
        )
        state = _make_state(suggested_fix=None, context=ctx)
        result = await ui_node(state)
        assert result["displayed"] is True

    @pytest.mark.asyncio
    async def test_log_contains_source(self):
        result = await ui_node(_make_state())
        assert "source=" in result["log"][0]
