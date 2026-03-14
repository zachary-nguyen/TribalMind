"""Tests for the Monitor node - error detection and classification."""

from __future__ import annotations

import pytest
from tribalmind.graph.monitor import (
    _classify_from_command,
    _generate_signature,
    _try_classify,
    monitor_node,
)
from tribalmind.graph.state import ShellEvent


class TestTryClassify:
    def test_python_module_not_found(self):
        t, p = _try_classify("ModuleNotFoundError: No module named 'requests'")
        assert t == "ModuleNotFoundError"
        assert p == "requests"

    def test_python_import_error(self):
        t, p = _try_classify("ImportError: cannot import name 'foo' from 'bar.baz'")
        assert t == "ImportError"
        assert p == "bar"

    def test_python_traceback(self):
        stderr = (
            "Traceback (most recent call last):\n"
            "  File \"main.py\"\nValueError: invalid literal"
        )
        t, p = _try_classify(stderr)
        assert t == "ValueError"

    def test_node_module_not_found(self):
        t, p = _try_classify("Error: Cannot find module 'express'")
        assert t == "NodeModuleNotFound"
        assert p == "express"

    def test_npm_404(self):
        stderr = "npm error 404 Not Found - GET https://registry.npmjs.org/sdfkxcjvlxc"
        t, p = _try_classify(stderr)
        assert t == "NpmPackageNotFound"
        assert p == "sdfkxcjvlxc"

    def test_npm_generic_error(self):
        t, p = _try_classify("npm ERR! missing script: build")
        assert t == "NpmError"

    def test_rust_error(self):
        t, _ = _try_classify("error[E0308]: mismatched types")
        assert t == "RustError"

    def test_go_panic(self):
        t, _ = _try_classify("panic: runtime error: index out of range")
        assert t == "GoPanic"

    def test_command_not_found(self):
        t, p = _try_classify("docker: command not found")
        assert t == "CommandNotFound"
        assert p == "docker"

    def test_permission_denied(self):
        t, _ = _try_classify("Permission denied: /usr/local/bin/test")
        assert t == "PermissionDenied"

    def test_pip_install_error(self):
        t, p = _try_classify("ERROR: No matching distribution found for nonexistent-pkg")
        assert t == "PipInstallError"
        assert p == "nonexistent-pkg"

    def test_empty_stderr(self):
        t, p = _try_classify("")
        assert t is None
        assert p is None

    def test_unrecognized_stderr(self):
        t, p = _try_classify("Some random output that doesn't match anything")
        assert t is None
        assert p is None


class TestClassifyFromCommand:
    def test_python_import(self):
        t, p = _classify_from_command("python -c \"import foo\"")
        assert t == "PythonError"
        assert p == "foo"

    def test_pip_install(self):
        t, p = _classify_from_command("pip install requests")
        assert t == "PipInstallError"
        assert p == "requests"

    def test_npm_install(self):
        t, p = _classify_from_command("npm i express")
        assert t == "NpmError"
        assert p == "express"

    def test_npm_run(self):
        t, _ = _classify_from_command("npm run build")
        assert t == "NpmError"

    def test_cargo_build(self):
        t, _ = _classify_from_command("cargo build")
        assert t == "CargoError"

    def test_unrecognized(self):
        t, p = _classify_from_command("ls -la")
        assert t is None
        assert p is None


class TestGenerateSignature:
    def test_same_input_same_signature(self):
        s1 = _generate_signature("python main.py", "ModuleNotFoundError: No module named 'foo'")
        s2 = _generate_signature("python main.py", "ModuleNotFoundError: No module named 'foo'")
        assert s1 == s2

    def test_different_errors_different_signature(self):
        s1 = _generate_signature("python main.py", "ModuleNotFoundError: No module named 'foo'")
        s2 = _generate_signature("python main.py", "ModuleNotFoundError: No module named 'bar'")
        assert s1 != s2

    def test_normalizes_versions(self):
        s1 = _generate_signature("pip install foo", "requires foo>=1.2.3")
        s2 = _generate_signature("pip install foo", "requires foo>=4.5.6")
        assert s1 == s2

    def test_normalizes_paths(self):
        s1 = _generate_signature("python", "Error in /home/user/project/main.py")
        s2 = _generate_signature("python", "Error in /tmp/other/main.py")
        assert s1 == s2

    def test_empty_stderr(self):
        sig = _generate_signature("false", "")
        assert sig and len(sig) == 16


class TestMonitorNode:
    @pytest.mark.asyncio
    async def test_successful_command(self, shell_event_success):
        result = await monitor_node({"event": shell_event_success})
        assert result["is_error"] is False
        assert result["error_signature"] == ""

    @pytest.mark.asyncio
    async def test_classifies_python_error(self, shell_event_python_error):
        result = await monitor_node({"event": shell_event_python_error})
        assert result["is_error"] is True
        assert result["error_type"] == "ModuleNotFoundError"
        assert result["error_package"] == "nonexistent_module"

    @pytest.mark.asyncio
    async def test_error_without_stderr_uses_command(self):
        event = ShellEvent(
            command="python -c \"import foo\"",
            exit_code=1,
            cwd="/tmp",
            timestamp=1710000000.0,
        )
        result = await monitor_node({"event": event})
        assert result["is_error"] is True
        assert result["error_type"] == "PythonError"
        assert result["error_package"] == "foo"

    @pytest.mark.asyncio
    async def test_unknown_error_leaves_type_none(self):
        event = ShellEvent(
            command="some-custom-tool",
            exit_code=1,
            cwd="/tmp",
            timestamp=1710000000.0,
        )
        result = await monitor_node({"event": event})
        assert result["is_error"] is True
        assert result["error_type"] is None
        assert result["error_signature"]

    @pytest.mark.asyncio
    async def test_log_includes_type(self):
        event = ShellEvent(
            command="npm install foo",
            exit_code=1,
            cwd="/project",
            timestamp=1710000000.0,
            stderr="npm ERR! 404 Not Found - GET https://registry.npmjs.org/foo",
        )
        result = await monitor_node({"event": event})
        assert "NpmPackageNotFound" in result["log"][0]
