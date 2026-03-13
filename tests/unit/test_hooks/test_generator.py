"""Tests for shell hook generator."""

from __future__ import annotations

import pytest

from tribalmind.hooks.generator import (
    SENTINEL_BEGIN,
    SENTINEL_END,
    detect_shell,
    install_hook,
    uninstall_hook,
)


class TestDetectShell:
    def test_detect_bash(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/bash")
        monkeypatch.delenv("PSModulePath", raising=False)
        assert detect_shell() == "bash"

    def test_detect_zsh(self, monkeypatch):
        monkeypatch.setenv("SHELL", "/bin/zsh")
        monkeypatch.delenv("PSModulePath", raising=False)
        assert detect_shell() == "zsh"

    def test_detect_powershell(self, monkeypatch):
        monkeypatch.delenv("SHELL", raising=False)
        monkeypatch.setenv("PSModulePath", "C:\\something")
        assert detect_shell() == "powershell"


class TestInstallHook:
    def test_install_bash_hook(self, tmp_path, monkeypatch):
        rc_file = tmp_path / ".bashrc"
        rc_file.write_text("# existing config\n")
        monkeypatch.setattr(
            "tribalmind.hooks.generator.get_rc_file",
            lambda shell: rc_file,
        )
        install_hook("bash")
        content = rc_file.read_text()
        assert SENTINEL_BEGIN in content
        assert SENTINEL_END in content
        assert "bash_hook.sh" in content

    def test_install_idempotent(self, tmp_path, monkeypatch):
        rc_file = tmp_path / ".bashrc"
        rc_file.write_text("# existing config\n")
        monkeypatch.setattr(
            "tribalmind.hooks.generator.get_rc_file",
            lambda shell: rc_file,
        )
        install_hook("bash")
        content_after_first = rc_file.read_text()
        install_hook("bash")
        content_after_second = rc_file.read_text()
        assert content_after_first == content_after_second

    def test_uninstall_hook(self, tmp_path, monkeypatch):
        rc_file = tmp_path / ".bashrc"
        rc_file.write_text(
            f"# before\n{SENTINEL_BEGIN}\nsource hook.sh\n{SENTINEL_END}\n# after\n"
        )
        monkeypatch.setattr(
            "tribalmind.hooks.generator.get_rc_file",
            lambda shell: rc_file,
        )
        uninstall_hook("bash")
        content = rc_file.read_text()
        assert SENTINEL_BEGIN not in content
        assert SENTINEL_END not in content
        assert "# before" in content
        assert "# after" in content
