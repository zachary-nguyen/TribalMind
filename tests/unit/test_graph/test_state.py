"""Tests for the LangGraph state definitions."""

from __future__ import annotations

from tribalmind.graph.state import ContextResult, ShellEvent


class TestShellEvent:
    def test_create(self):
        event = ShellEvent(
            command="ls -la",
            exit_code=0,
            cwd="/home/user",
            timestamp=1710000000.0,
        )
        assert event.command == "ls -la"
        assert event.exit_code == 0
        assert event.stderr == ""

    def test_with_stderr(self):
        event = ShellEvent(
            command="python fail.py",
            exit_code=1,
            cwd="/tmp",
            timestamp=1710000000.0,
            stderr="Error occurred",
        )
        assert event.stderr == "Error occurred"


class TestContextResult:
    def test_empty_has_no_matches(self):
        ctx = ContextResult()
        assert not ctx.has_matches

    def test_with_local_matches(self):
        ctx = ContextResult(local_matches=[{"content": "fix"}])
        assert ctx.has_matches

    def test_with_upstream_info(self):
        ctx = ContextResult(upstream_info={"repo": "test/repo"})
        assert ctx.has_matches
