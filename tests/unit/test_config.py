"""Tests for configuration management."""

from __future__ import annotations

from pathlib import Path

import yaml
from tribalmind.config.settings import TribalSettings, clear_settings_cache


class TestTribalSettings:
    def test_defaults(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TRIBAL_BACKBOARD_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)  # avoid local tribal.yaml
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.backboard_base_url == "https://app.backboard.io/api"
        assert settings.llm_provider == "anthropic"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("TRIBAL_LLM_PROVIDER", "openai")
        settings = TribalSettings()
        assert settings.llm_provider == "openai"

    def test_yaml_loading(self, tmp_path, monkeypatch):
        config = {"llm_provider": "google", "model_name": "gemini-pro"}
        config_file = tmp_path / "tribal.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.llm_provider == "google"
        assert settings.model_name == "gemini-pro"

    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        config = {"llm_provider": "google"}
        config_file = tmp_path / "tribal.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TRIBAL_LLM_PROVIDER", "openai")
        settings = TribalSettings()
        assert settings.llm_provider == "openai"

    def test_extra_fields_ignored(self, tmp_path, monkeypatch):
        """Old config files with removed fields should not break."""
        config = {"daemon_port": 8888, "watch_dirs": ["/dev"], "llm_provider": "google"}
        config_file = tmp_path / "tribal.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.llm_provider == "google"

    def test_properties(self):
        settings = TribalSettings()
        assert isinstance(settings.config_dir, Path)
        assert isinstance(settings.data_dir, Path)
