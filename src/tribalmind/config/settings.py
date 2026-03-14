"""Configuration management using Pydantic Settings.

Loads settings from: defaults -> tribal.yaml -> environment variables (TRIBAL_ prefix).
Searches for tribal.yaml in CWD, then walks up to git root, then user config dir.
"""

from __future__ import annotations

import subprocess
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


def _find_yaml_config() -> Path | None:
    """Search for tribal.yaml in CWD -> git root -> user config dir."""
    cwd = Path.cwd()

    # Check CWD
    candidate = cwd / "tribal.yaml"
    if candidate.exists():
        return candidate

    # Walk up to git root
    git_root = _find_git_root(cwd)
    if git_root and git_root != cwd:
        candidate = git_root / "tribal.yaml"
        if candidate.exists():
            return candidate

    # Check user config dir
    config_dir = Path(platformdirs.user_config_dir("tribalmind"))
    candidate = config_dir / "tribal.yaml"
    if candidate.exists():
        return candidate

    return None


def _load_yaml_settings() -> dict[str, Any]:
    """Load settings from the discovered tribal.yaml file."""
    config_path = _find_yaml_config()
    if config_path is None:
        return {}
    with open(config_path) as f:
        data = yaml.safe_load(f)
    return data if isinstance(data, dict) else {}


class TribalSettings(BaseSettings):
    """TribalMind configuration model.

    Priority: env vars (TRIBAL_ prefix) > tribal.yaml > defaults.
    """

    model_config = SettingsConfigDict(
        env_prefix="TRIBAL_",
        env_nested_delimiter="__",
    )

    # Backboard
    backboard_base_url: str = "https://app.backboard.io/api"
    backboard_api_key: str = ""

    # Project
    project_root: Path = Field(default_factory=Path.cwd)
    project_assistant_id: str | None = None
    org_assistant_id: str | None = None

    # LLM (via Backboard's multi-provider model selection)
    llm_provider: str = "anthropic"
    model_name: str = "claude-sonnet-4-20250514"

    # Embedding (permanent per Backboard assistant - choose carefully)
    embedding_provider: str = "openai"
    embedding_model: str = "text-embedding-3-small"
    embedding_dims: int = 1536

    # Daemon
    daemon_host: str = "127.0.0.1"
    daemon_port: int = 7483

    # GitHub (optional upstream monitoring)
    github_token: str = ""

    # Team sharing
    team_sharing_enabled: bool = False

    # Ignore patterns for shell monitoring
    ignore_commands: list[str] = Field(
        default_factory=lambda: ["cd", "ls", "pwd", "clear", "cls", "echo", "cat", "less", "more"]
    )

    # Directory filter — if non-empty, only monitor commands run inside these paths
    watch_dirs: list[Path] = Field(default_factory=list)

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

    @property
    def runtime_dir(self) -> Path:
        """Runtime directory (PID files, sockets)."""
        return Path(platformdirs.user_runtime_dir("tribalmind"))

    @property
    def pid_file(self) -> Path:
        """Path to daemon PID file."""
        return self.runtime_dir / "daemon.pid"

    @property
    def log_file(self) -> Path:
        """Path to daemon log file."""
        return self.data_dir / "daemon.log"


@lru_cache(maxsize=1)
def get_settings() -> TribalSettings:
    """Get the singleton settings instance."""
    return TribalSettings()


def clear_settings_cache() -> None:
    """Clear the cached settings (useful for testing or config reload)."""
    get_settings.cache_clear()
