"""Tests for the Monitor node - error parsing and classification."""

from __future__ import annotations

import pytest
from tribalmind.graph.monitor import monitor_node, parse_error
from tribalmind.graph.state import ShellEvent


class TestParseError:
    def test_python_module_not_found(self):
        stderr = "ModuleNotFoundError: No module named 'requests'"
        result = parse_error(stderr)
        assert result.error_type == "ModuleNotFoundError"
        assert result.package == "requests"
        assert result.signature

    def test_python_import_error(self):
        stderr = "ImportError: cannot import name 'foo' from 'bar.baz'"
        result = parse_error(stderr)
        assert result.error_type == "ImportError"
        assert result.package == "bar"

    def test_python_traceback(self):
        stderr = (
            "Traceback (most recent call last):\n"
            '  File "main.py", line 1\n'
            "ValueError: invalid literal\n"
        )
        result = parse_error(stderr)
        assert result.error_type == "ValueError"
        assert "invalid literal" in result.message

    def test_node_module_not_found(self):
        stderr = "Error: Cannot find module 'express'"
        result = parse_error(stderr)
        assert result.error_type == "ModuleNotFoundError"
        assert result.package == "express"

    def test_npm_error(self):
        stderr = "npm ERR! 404 Not Found - fake-package"
        result = parse_error(stderr)
        assert result.error_type == "NpmError"

    def test_rust_error(self):
        stderr = "error[E0308]: mismatched types"
        result = parse_error(stderr)
        assert result.error_type == "RustError[E0308]"
        assert "mismatched types" in result.message

    def test_go_panic(self):
        stderr = "panic: runtime error: index out of range"
        result = parse_error(stderr)
        assert result.error_type == "GoPanic"

    def test_command_not_found(self):
        stderr = "docker: command not found"
        result = parse_error(stderr)
        assert result.error_type == "CommandNotFound"
        assert result.package == "docker"

    def test_permission_denied(self):
        stderr = "Permission denied: /usr/local/bin/test"
        result = parse_error(stderr)
        assert result.error_type == "PermissionDenied"

    def test_empty_stderr(self):
        result = parse_error("")
        assert result.error_type == ""
        assert result.signature == ""

    def test_signature_stability(self):
        """Same error should produce the same signature."""
        stderr1 = "ModuleNotFoundError: No module named 'foo'"
        stderr2 = "ModuleNotFoundError: No module named 'foo'"
        r1 = parse_error(stderr1)
        r2 = parse_error(stderr2)
        assert r1.signature == r2.signature

    def test_signature_differs_for_different_errors(self):
        r1 = parse_error("ModuleNotFoundError: No module named 'foo'")
        r2 = parse_error("ModuleNotFoundError: No module named 'bar'")
        assert r1.signature != r2.signature


class TestMonitorNode:
    @pytest.mark.asyncio
    async def test_successful_command(self, shell_event_success):
        result = await monitor_node({"event": shell_event_success})
        assert result["is_error"] is False
        assert result["error_signature"] == ""

    @pytest.mark.asyncio
    async def test_python_error(self, shell_event_python_error):
        result = await monitor_node({"event": shell_event_python_error})
        assert result["is_error"] is True
        assert result["error_type"] == "ModuleNotFoundError"
        assert result["error_package"] == "nonexistent_module"
        assert result["error_signature"]

    @pytest.mark.asyncio
    async def test_error_without_stderr(self):
        event = ShellEvent(
            command="false",
            exit_code=1,
            cwd="/tmp",
            timestamp=1710000000.0,
        )
        result = await monitor_node({"event": event})
        assert result["is_error"] is True
        # No stderr means no error type can be detected
        assert result["error_type"] is None
