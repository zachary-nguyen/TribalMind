"""Tests for configuration management."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from tribalmind.config.settings import TribalSettings, _find_yaml_config, clear_settings_cache


class TestTribalSettings:
    def test_defaults(self, monkeypatch):
        monkeypatch.delenv("TRIBAL_BACKBOARD_API_KEY", raising=False)
        settings = TribalSettings()
        assert settings.backboard_base_url == "https://app.backboard.io/api"
        assert settings.daemon_host == "127.0.0.1"
        assert settings.daemon_port == 7483
        assert settings.team_sharing_enabled is False
        assert settings.llm_provider == "anthropic"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TRIBAL_DAEMON_PORT", "9999")
        monkeypatch.setenv("TRIBAL_LLM_PROVIDER", "openai")
        settings = TribalSettings()
        assert settings.daemon_port == 9999
        assert settings.llm_provider == "openai"

    def test_yaml_loading(self, tmp_path, monkeypatch):
        config = {"daemon_port": 8888, "llm_provider": "google"}
        config_file = tmp_path / "tribal.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.daemon_port == 8888
        assert settings.llm_provider == "google"

    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        config = {"daemon_port": 8888}
        config_file = tmp_path / "tribal.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TRIBAL_DAEMON_PORT", "7777")
        settings = TribalSettings()
        assert settings.daemon_port == 7777

    def test_ignore_commands_default(self):
        settings = TribalSettings()
        assert "cd" in settings.ignore_commands
        assert "ls" in settings.ignore_commands

    def test_properties(self):
        settings = TribalSettings()
        assert isinstance(settings.config_dir, Path)
        assert isinstance(settings.data_dir, Path)
        assert isinstance(settings.runtime_dir, Path)
        assert settings.pid_file.name == "daemon.pid"
