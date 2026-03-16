"""Credential management using system keyring.

Stores API keys in the OS-native credential store (Windows Credential Manager,
macOS Keychain, Linux Secret Service). Falls back to environment variables / config
when no keyring backend is available (common on minimal Linux installs like Arch).
"""

from __future__ import annotations

import keyring
import keyring.errors
from rich.console import Console

SERVICE_PREFIX = "tribalmind"

# Known credential keys
BACKBOARD_API_KEY = "backboard_api_key"

console = Console(stderr=True)

_keyring_warned = False


def _warn_no_keyring() -> None:
    global _keyring_warned
    if not _keyring_warned:
        console.print(
            "[yellow]Warning:[/yellow] No system keyring backend found. "
            "Credentials will fall back to config file / environment variables.\n"
            "To enable keyring support, install a secret-service provider "
            "(e.g. gnome-keyring, kwallet) or the keyrings.alt package."
        )
        _keyring_warned = True


def _service_name(key: str) -> str:
    return f"{SERVICE_PREFIX}:{key}"


def set_credential(key: str, value: str) -> bool:
    """Store a credential in the system keyring.

    Returns True if stored successfully, False if keyring is unavailable.
    """
    try:
        keyring.set_password(_service_name(key), key, value.strip())
        return True
    except keyring.errors.NoKeyringError:
        _warn_no_keyring()
        return False


def get_credential(key: str) -> str | None:
    """Retrieve a credential from the system keyring."""
    try:
        value = keyring.get_password(_service_name(key), key)
    except keyring.errors.NoKeyringError:
        _warn_no_keyring()
        return None
    return value.strip() if value else value


def delete_credential(key: str) -> None:
    """Remove a credential from the system keyring."""
    try:
        keyring.delete_password(_service_name(key), key)
    except (keyring.errors.PasswordDeleteError, keyring.errors.NoKeyringError):
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
