"""Tests for the provider factory."""

from __future__ import annotations

import pytest
from tribalmind.providers.backboard_provider import BackboardProvider
from tribalmind.providers.factory import (
    _REGISTRY,
    get_provider,
    get_provider_choices,
    register_provider,
)


class TestGetProviderChoices:
    def test_returns_backboard_and_mem0(self):
        choices = get_provider_choices()
        names = [name for _, name, _ in choices]
        assert "backboard" in names
        assert "mem0" in names

    def test_backboard_is_first(self):
        choices = get_provider_choices()
        assert choices[0][1] == "backboard"

    def test_returns_tuples(self):
        choices = get_provider_choices()
        for label, name, coming_soon in choices:
            assert isinstance(label, str)
            assert isinstance(name, str)
            assert isinstance(coming_soon, bool)


class TestGetProvider:
    def test_backboard_default(self, settings):
        provider = get_provider("backboard")
        assert isinstance(provider, BackboardProvider)

    def test_unknown_provider_raises(self, settings):
        with pytest.raises(ValueError, match="Unknown memory provider"):
            get_provider("nonexistent")

    def test_defaults_to_settings_provider(self, monkeypatch, settings):
        monkeypatch.setenv("TRIBAL_PROVIDER", "backboard")
        provider = get_provider()
        assert isinstance(provider, BackboardProvider)

    def test_mem0_without_api_key_raises(self, monkeypatch, tmp_path):
        # Ensure clean settings with no mem0 config from YAML
        monkeypatch.setenv("TRIBAL_BACKBOARD_API_KEY", "test-key")
        monkeypatch.setenv("TRIBAL_PROJECT_ROOT", str(tmp_path))
        monkeypatch.setenv("TRIBAL_PROJECT_ASSISTANT_ID", "test-123")
        monkeypatch.delenv("TRIBAL_MEM0_API_KEY", raising=False)
        monkeypatch.chdir(tmp_path)  # avoid picking up .tribal/config.yaml

        from tribalmind.config.settings import clear_settings_cache
        clear_settings_cache()

        with pytest.raises(ValueError, match="Mem0 API key not configured"):
            get_provider("mem0")


class TestRegisterProvider:
    def test_register_custom_provider(self):
        def build(settings):
            return BackboardProvider()

        register_provider("custom-test", "Custom Test Provider", build)
        assert "custom-test" in _REGISTRY

        choices = get_provider_choices()
        names = [name for _, name, _ in choices]
        assert "custom-test" in names

        # Clean up
        del _REGISTRY["custom-test"]

    def test_register_coming_soon(self):
        def build(settings):
            raise NotImplementedError

        register_provider("future-test", "Future Provider", build, coming_soon=True)
        assert _REGISTRY["future-test"][2] is True

        with pytest.raises(ValueError, match="not yet available"):
            get_provider("future-test")

        # Clean up
        del _REGISTRY["future-test"]
