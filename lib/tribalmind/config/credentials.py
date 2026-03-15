"""Credential management using system keyring.

Stores API keys in the OS-native credential store (Windows Credential Manager,
macOS Keychain, Linux Secret Service). Falls back to environment variables / config.
"""

from __future__ import annotations

import keyring
from rich.console import Console

SERVICE_PREFIX = "tribalmind"

# Known credential keys
BACKBOARD_API_KEY = "backboard_api_key"

console = Console(stderr=True)


def _service_name(key: str) -> str:
    return f"{SERVICE_PREFIX}:{key}"


def set_credential(key: str, value: str) -> None:
    """Store a credential in the system keyring."""
    keyring.set_password(_service_name(key), key, value.strip())


def get_credential(key: str) -> str | None:
    """Retrieve a credential from the system keyring."""
    value = keyring.get_password(_service_name(key), key)
    return value.strip() if value else value


def delete_credential(key: str) -> None:
    """Remove a credential from the system keyring."""
    try:
        keyring.delete_password(_service_name(key), key)
    except keyring.errors.PasswordDeleteError:
        pass


def get_backboard_api_key() -> str | None:
    """Get the Backboard API key, preferring keyring over config/env."""
    from tribalmind.config.settings import get_settings

    # Try keyring first
    key = get_credential(BACKBOARD_API_KEY)
    if key:
        return key

    # Fall back to settings (env var or yaml)
    settings = get_settings()
    return settings.backboard_api_key or None



def require_backboard_api_key() -> str:
    """Get the Backboard API key or exit with an error message."""
    key = get_backboard_api_key()
    if not key:
        console.print(
            "[bold red]Backboard API key not configured.[/bold red]\n"
            "Run [bold]tribal config set-secret backboard-api-key[/bold] to set it,\n"
            "or set the TRIBAL_BACKBOARD_API_KEY environment variable."
        )
        raise SystemExit(1)
    return key
