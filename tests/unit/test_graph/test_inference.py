"""Tests for the inference node."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from tribalmind.backboard.memory import MemoryEntry
from tribalmind.graph.inference import (
    LLM_FIX_CONFIDENCE,
    LOCAL_FIX_CONFIDENCE,
    _build_llm_prompt,
    _cache_get,
    _cache_put,
    _llm_cache,
    _parse_llm_response,
    _query_llm,
    _recent_signatures,
    _try_local_fix,
    inference_node,
)
from tribalmind.graph.state import ContextResult, ShellEvent, TribalState


def _make_state(**overrides) -> TribalState:
    base: TribalState = {
        "is_error": True,
        "error_signature": "abc123",
        "error_package": None,
        "error_type": None,
        "has_known_fix": False,
        "context": ContextResult(),
        "event": ShellEvent(
            command="python -c 'import requests'",
            exit_code=1,
            cwd="/project",
            timestamp=1710000000.0,
            stderr="ModuleNotFoundError: No module named 'requests'",
        ),
    }
    base.update(overrides)
    return base


@pytest.fixture(autouse=True)
def _clear_caches():
    """Clear inference caches between tests."""
    _llm_cache.clear()
    _recent_signatures.clear()
    yield
    _llm_cache.clear()
    _recent_signatures.clear()


class TestTryLocalFix:
    def test_module_not_found(self):
        assert _try_local_fix("ModuleNotFoundError", "requests") == "pip install requests"

    def test_node_module(self):
        assert _try_local_fix("NodeModuleNotFound", "express") == "npm install express"

    def test_command_not_found(self):
        fix = _try_local_fix("CommandNotFound", "docker")
        assert "docker" in fix

    def test_no_package_needed(self):
        assert _try_local_fix("ModuleNotFoundError", None) is None

    def test_unknown_type(self):
        assert _try_local_fix("WeirdError", "foo") is None

    def test_none_type(self):
        assert _try_local_fix(None, "foo") is None


class TestLlmCache:
    def test_cache_hit(self):
        _cache_put("sig1", {"fix": "pip install foo"})
        assert _cache_get("sig1") == {"fix": "pip install foo"}

    def test_cache_miss(self):
        assert _cache_get("nonexistent") is None

    def test_cache_expiry(self):
        import time
        _llm_cache["sig-old"] = ({"fix": "old"}, time.time() - 7200)
        assert _cache_get("sig-old") is None


class TestBuildLlmPrompt:
    def test_includes_command(self):
        prompt = _build_llm_prompt(_make_state())
        assert "python -c" in prompt

    def test_includes_stderr(self):
        prompt = _build_llm_prompt(_make_state())
        assert "ModuleNotFoundError" in prompt

    def test_includes_upstream_info(self):
        ctx = ContextResult(
            upstream_info={
                "known_issues": "issue #42: timeout bug",
                "latest_version": "2.32.0",
            }
        )
        prompt = _build_llm_prompt(_make_state(context=ctx))
        assert "issue #42" in prompt
        assert "2.32.0" in prompt

    def test_asks_for_json(self):
        prompt = _build_llm_prompt(_make_state())
        assert "JSON" in prompt
        assert "is_valid_package" in prompt


class TestParseLlmResponse:
    def test_parses_json(self):
        resp = {"content": (
            '{"error_type": "ModuleNotFoundError",'
            ' "package": "requests",'
            ' "fix": "pip install requests",'
            ' "is_valid_package": true}'
        )}
        result = _parse_llm_response(resp)
        assert result["error_type"] == "ModuleNotFoundError"
        assert result["is_valid_package"] is True

    def test_strips_code_fences(self):
        resp = {"content": '```json\n{"error_type": "NpmError", "fix": "npm install"}\n```'}
        result = _parse_llm_response(resp)
        assert result["error_type"] == "NpmError"

    def test_invalid_json_fallback(self):
        resp = {"content": "pip install requests"}
        result = _parse_llm_response(resp)
        assert result["fix"] == "pip install requests"

    def test_empty_content(self):
        assert _parse_llm_response({"content": ""}) is None

    def test_empty_response(self):
        assert _parse_llm_response({}) is None


class TestQueryLlm:
    @pytest.mark.asyncio
    async def test_returns_parsed_result(self, monkeypatch, mock_backboard_client):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")

        mock_backboard_client.post = AsyncMock(
            side_effect=[
                {"thread_id": "thread-1"},
                {"content": (
                    '{"error_type": "ModuleNotFoundError",'
                    ' "fix": "pip install requests",'
                    ' "is_valid_package": true}'
                )},
            ]
        )
        mock_backboard_client.delete = AsyncMock(return_value={})

        with patch(
            "tribalmind.backboard.client.create_client",
            return_value=mock_backboard_client,
        ):
            result = await _query_llm(_make_state())

        assert result is not None
        assert result["fix"] == "pip install requests"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_assistant(self, monkeypatch):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "")
        assert await _query_llm(_make_state()) is None

    @pytest.mark.asyncio
    async def test_handles_api_error(self, monkeypatch, mock_backboard_client):
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "asst-proj")

        mock_backboard_client.__aenter__ = AsyncMock(side_effect=Exception("fail"))

        with patch(
            "tribalmind.backboard.client.create_client",
            return_value=mock_backboard_client,
        ):
            assert await _query_llm(_make_state()) is None


class TestInferenceNode:
    @pytest.mark.asyncio
    async def test_stage1_memory_match(self):
        match = MemoryEntry(content="test", fix_text="pip install requests", relevance_score=0.92)
        ctx = ContextResult(local_matches=[match])
        state = _make_state(has_known_fix=True, context=ctx)

        result = await inference_node(state)
        assert result["suggested_fix"] == "pip install requests"
        assert result["fix_confidence"] == 0.92
        assert "source=memory" in result["log"][0]

    @pytest.mark.asyncio
    async def test_stage2_local_fix(self):
        """Monitor classified it — no LLM needed."""
        state = _make_state(
            error_type="ModuleNotFoundError",
            error_package="requests",
            has_known_fix=False,
        )

        with patch("tribalmind.graph.inference._query_llm", new_callable=AsyncMock) as mock_llm:
            result = await inference_node(state)

        mock_llm.assert_not_called()
        assert result["suggested_fix"] == "pip install requests"
        assert result["fix_confidence"] == LOCAL_FIX_CONFIDENCE
        assert "source=local" in result["log"][0]

    @pytest.mark.asyncio
    async def test_stage3_cache_hit(self):
        """Same signature should hit cache, no LLM call."""
        _cache_put("abc123", {
            "error_type": "NpmError",
            "package": "express",
            "fix": "npm install express",
            "is_valid_package": True,
        })

        state = _make_state(error_signature="abc123", has_known_fix=False)

        with patch("tribalmind.graph.inference._query_llm", new_callable=AsyncMock) as mock_llm:
            result = await inference_node(state)

        mock_llm.assert_not_called()
        assert result["suggested_fix"] == "npm install express"
        assert "source=cache" in result["log"][0]

    @pytest.mark.asyncio
    async def test_stage3_llm_fallback(self):
        state = _make_state(has_known_fix=False)

        with patch(
            "tribalmind.graph.inference._query_llm",
            new_callable=AsyncMock,
            return_value={
                "error_type": "ModuleNotFoundError",
                "package": "requests",
                "fix": "pip install requests",
                "is_valid_package": True,
            },
        ):
            result = await inference_node(state)

        assert result["suggested_fix"] == "pip install requests"
        assert result["fix_confidence"] == LLM_FIX_CONFIDENCE
        assert "source=llm" in result["log"][0]
        # Should be cached now
        assert _cache_get("abc123") is not None

    @pytest.mark.asyncio
    async def test_invalid_package_shows_explanation(self):
        state = _make_state(has_known_fix=False)

        with patch(
            "tribalmind.graph.inference._query_llm",
            new_callable=AsyncMock,
            return_value={
                "error_type": "NpmPackageNotFound",
                "package": "sdfkxcjvlxc",
                "fix": "npm install sdfkxcjvlxc",
                "is_valid_package": False,
                "explanation": "Package 'sdfkxcjvlxc' does not exist on npm",
            },
        ):
            result = await inference_node(state)

        assert "does not exist" in result["suggested_fix"]
        assert result["fix_confidence"] == 0.9

    @pytest.mark.asyncio
    async def test_no_fix_found(self):
        state = _make_state(has_known_fix=False)

        with patch(
            "tribalmind.graph.inference._query_llm",
            new_callable=AsyncMock, return_value=None,
        ):
            result = await inference_node(state)

        assert result["suggested_fix"] is None
        assert "source=none" in result["log"][0]

    @pytest.mark.asyncio
    async def test_skips_llm_when_not_error(self):
        state = _make_state(is_error=False, has_known_fix=False)

        with patch("tribalmind.graph.inference._query_llm", new_callable=AsyncMock) as mock_llm:
            result = await inference_node(state)

        mock_llm.assert_not_called()
        assert result["suggested_fix"] is None

    @pytest.mark.asyncio
    async def test_memory_preferred_over_local(self):
        """Memory fix should be used even when local fix is available."""
        match = MemoryEntry(content="x", fix_text="special fix", relevance_score=0.85)
        ctx = ContextResult(local_matches=[match])
        state = _make_state(
            has_known_fix=True,
            context=ctx,
            error_type="ModuleNotFoundError",
            error_package="requests",
        )

        result = await inference_node(state)
        assert result["suggested_fix"] == "special fix"
        assert "source=memory" in result["log"][0]
