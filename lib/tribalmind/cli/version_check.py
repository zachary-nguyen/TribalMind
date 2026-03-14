"""Version check and upgrade prompt.

Fetches latest stable version from PyPI and, if the current install is older,
prompts the user to run the upgrade command.
"""

from __future__ import annotations

import httpx
from packaging.version import InvalidVersion, Version
from rich.console import Console

from tribalmind import __version__

PYPI_URL = "https://pypi.org/pypi/tribalmind/json"
TIMEOUT = 3.0
CONSOLE = Console(stderr=True)


def get_latest_version() -> str | None:
    """Fetch latest stable version from PyPI. Returns None on error or timeout."""
    try:
        with httpx.Client(timeout=TIMEOUT) as client:
            r = client.get(PYPI_URL)
            r.raise_for_status()
            data = r.json()
    except Exception:
        return None

    raw = data.get("info", {}).get("version")
    if not raw:
        return None
    try:
        v = Version(raw)
        if v.is_prerelease or v.is_devrelease:
            # Prefer latest non-prerelease from releases if available
            releases = data.get("releases") or {}
            for rev in sorted(releases.keys(), key=lambda x: Version(x), reverse=True):
                ver = Version(rev)
                if not ver.is_prerelease and not ver.is_devrelease:
                    return rev
        return raw
    except InvalidVersion:
        return raw
    return None


def is_outdated(current: str, latest: str) -> bool:
    """Return True if current is strictly older than latest."""
    try:
        return Version(current) < Version(latest)
    except InvalidVersion:
        return False


def print_upgrade_notice(latest: str) -> None:
    """Print a notice asking the user to upgrade."""
    CONSOLE.print(
        "\n[bold yellow]A new version of TribalMind is available.[/] "
        "Upgrade with:\n  [bold cyan]pip install -U tribalmind[/]\n",
        highlight=False,
    )


def check_and_notify(skip: bool = False) -> None:
    """If current version is outdated, print upgrade notice. No-op if skip or on error."""
    if skip:
        return
    latest = get_latest_version()
    if latest is None:
        return
    if is_outdated(__version__, latest):
        print_upgrade_notice(latest)
