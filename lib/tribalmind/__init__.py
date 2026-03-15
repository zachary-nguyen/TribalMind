"""TribalMind - Shared memory for AI development agents."""

from __future__ import annotations


def _get_version() -> str:
    try:
        from importlib.metadata import version
        return version("tribalmind")
    except Exception:
        return "0.0.0.dev0"

__version__ = _get_version()
