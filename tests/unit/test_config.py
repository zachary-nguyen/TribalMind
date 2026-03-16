"""Tests for configuration management."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from tribalmind.config.settings import TribalSettings, clear_settings_cache


@pytest.fixture(autouse=True)
def _isolate_config(tmp_path, monkeypatch):
    """Prevent the real global config from leaking into tests."""
    fake_config_dir = str(tmp_path / "_global_config")
    monkeypatch.setattr("tribalmind.config.settings.platformdirs.user_config_dir", lambda *a, **kw: fake_config_dir)
    clear_settings_cache()


class TestTribalSettings:
    def test_defaults(self, tmp_path, monkeypatch):
        monkeypatch.delenv("TRIBAL_BACKBOARD_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)
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
        config_dir = tmp_path / ".tribal"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.llm_provider == "google"
        assert settings.model_name == "gemini-pro"

    def test_legacy_yaml_fallback(self, tmp_path, monkeypatch):
        """Legacy tribal.yaml in project root should still be discovered."""
        config = {"llm_provider": "google", "model_name": "gemini-pro"}
        config_file = tmp_path / "tribal.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.llm_provider == "google"
        assert settings.model_name == "gemini-pro"

    def test_new_config_takes_priority_over_legacy(self, tmp_path, monkeypatch):
        """New .tribal/config.yaml should win over legacy tribal.yaml."""
        legacy = {"llm_provider": "google"}
        (tmp_path / "tribal.yaml").write_text(yaml.dump(legacy))

        new = {"llm_provider": "openai"}
        config_dir = tmp_path / ".tribal"
        config_dir.mkdir()
        (config_dir / "config.yaml").write_text(yaml.dump(new))

        monkeypatch.chdir(tmp_path)
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.llm_provider == "openai"

    def test_env_overrides_yaml(self, tmp_path, monkeypatch):
        config = {"llm_provider": "google"}
        config_dir = tmp_path / ".tribal"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("TRIBAL_LLM_PROVIDER", "openai")
        settings = TribalSettings()
        assert settings.llm_provider == "openai"

    def test_extra_fields_ignored(self, tmp_path, monkeypatch):
        """Old config files with removed fields should not break."""
        config = {"daemon_port": 8888, "watch_dirs": ["/dev"], "llm_provider": "google"}
        config_dir = tmp_path / ".tribal"
        config_dir.mkdir()
        config_file = config_dir / "config.yaml"
        config_file.write_text(yaml.dump(config))
        monkeypatch.chdir(tmp_path)
        clear_settings_cache()
        settings = TribalSettings()
        assert settings.llm_provider == "google"

    def test_properties(self):
        settings = TribalSettings()
        assert isinstance(settings.config_dir, Path)
        assert isinstance(settings.data_dir, Path)
