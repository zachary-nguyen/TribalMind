"""Configuration management using Pydantic Settings.

Loads settings from: defaults -> .tribal/config.yaml -> environment variables (TRIBAL_ prefix).
Searches for .tribal/config.yaml in CWD, then walks up to git root, then user config dir.
Falls back to legacy tribal.yaml locations for backwards compatibility.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import platformdirs
import yaml
from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_git_root(start: Path) -> Path | None:
    """Walk up from start to find the nearest .git directory."""
    current = start.resolve()
    for parent in [current, *current.parents]:
        if (parent / ".git").exists():
            return parent
    return None


def _first_existing(*paths: Path) -> Path | None:
    """Return the first path that exists, or None."""
    for p in paths:
        if p.exists():
            return p
    return None


def _find_yaml_configs() -> list[Path]:
    """Find all config files, ordered from lowest to highest priority.

    Looks for .tribal/config.yaml first, falling back to legacy tribal.yaml.
    Returns: [user config dir, git root, CWD] — only those that exist.
    Later entries override earlier ones when merged.
    """
    candidates: list[Path] = []
    cwd = Path.cwd()

    # Lowest priority: user config dir (global — no .tribal/ subfolder)
    config_dir = Path(platformdirs.user_config_dir("tribalmind"))
    candidate = config_dir / "tribal.yaml"
    if candidate.exists():
        candidates.append(candidate)

    # Mid priority: git root (if different from CWD)
    git_root = _find_git_root(cwd)
    if git_root and git_root != cwd:
        found = _first_existing(
            git_root / ".tribal" / "config.yaml",
            git_root / "tribal.yaml",  # legacy fallback
        )
        if found:
            candidates.append(found)

    # Highest priority: CWD
    found = _first_existing(
        cwd / ".tribal" / "config.yaml",
        cwd / "tribal.yaml",  # legacy fallback
    )
    if found:
        candidates.append(found)

    return candidates


def _load_yaml_settings() -> dict[str, Any]:
    """Load and merge settings from all discovered tribal.yaml files.

    User-level config is the base; project-level configs override scalar
    values but list values (like watch_dirs) are merged.
    """
    configs = _find_yaml_configs()
    if not configs:
        return {}

    merged: dict[str, Any] = {}
    for path in configs:
        with open(path) as f:
            data = yaml.safe_load(f)
        if not isinstance(data, dict):
            continue
        for key, val in data.items():
            # For list values, merge instead of replacing
            if isinstance(val, list) and isinstance(merged.get(key), list):
                seen = set(str(v) for v in merged[key])
                for item in val:
                    if str(item) not in seen:
                        merged[key].append(item)
                        seen.add(str(item))
            else:
                merged[key] = val
    return merged


class TribalSettings(BaseSettings):
    """TribalMind configuration model.

    Priority: env vars (TRIBAL_ prefix) > .tribal/config.yaml > defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="TRIBAL_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    # Memory provider (backboard, mem0, etc.)
    provider: str = "backboard"

    # Backboard
    backboard_base_url: str = "https://app.backboard.io/api"
    backboard_api_key: str = ""

    # Mem0 (optional — only needed when provider=mem0)
    mem0_api_key: str = ""
    mem0_org_id: str = ""
    mem0_project_id: str = ""

    # Project
    project_root: Path = Field(default_factory=Path.cwd)
    project_assistant_id: str | None = None

    # Limits
    max_memories_per_assistant: int = 500

    # LLM (via Backboard's multi-provider model selection)
    llm_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-20250514"

    @model_validator(mode="before")
    @classmethod
    def _merge_yaml(cls, values: dict[str, Any]) -> dict[str, Any]:
        """Merge YAML config as lowest-priority source (defaults < yaml < env)."""
        yaml_data = _load_yaml_settings()
        # YAML values are used only if not already set by env vars
        for key, val in yaml_data.items():
            if key not in values or values[key] is None:
                values[key] = val
        return values

    @property
    def config_dir(self) -> Path:
        """User config directory for TribalMind."""
        return Path(platformdirs.user_config_dir("tribalmind"))

    @property
    def data_dir(self) -> Path:
        """User data directory for TribalMind."""
        return Path(platformdirs.user_data_dir("tribalmind"))



@lru_cache(maxsize=1)
def get_settings() -> TribalSettings:
    """Get the singleton settings instance."""
    return TribalSettings()


def clear_settings_cache() -> None:
    """Clear the cached settings (useful for testing or config reload)."""
    get_settings.cache_clear()
