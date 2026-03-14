"""Upgrade command - install latest TribalMind from PyPI."""

from __future__ import annotations

import subprocess
import sys

import typer


def upgrade() -> None:
    """Upgrade TribalMind to the latest version from PyPI.

    Runs: pip install -U tribalmind
    """
    typer.echo("Upgrading TribalMind...")
    result = subprocess.run(
        [sys.executable, "-m", "pip", "install", "-U", "tribalmind"],
        capture_output=False,
    )
    if result.returncode != 0:
        raise typer.Exit(result.returncode)
