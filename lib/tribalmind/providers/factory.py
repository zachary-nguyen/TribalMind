"""Provider factory — resolves a provider name to a configured instance.

New providers are registered by adding an entry to _REGISTRY.
"""

from __future__ import annotations

from typing import Any

from tribalmind.providers.base import MemoryProvider

# Registry: name -> (label, builder_function, coming_soon)
# builder_function receives TribalSettings and returns a MemoryProvider
_REGISTRY: dict[str, tuple[str, Any, bool]] = {}


def _register_builtin_providers() -> None:
    """Register the built-in providers."""

    def _build_backboard(settings) -> MemoryProvider:
        from tribalmind.providers.backboard_provider import BackboardProvider

        return BackboardProvider(assistant_id=settings.project_assistant_id or "")

    def _build_mem0(settings) -> MemoryProvider:
        from tribalmind.providers.mem0_provider import Mem0Provider

        api_key = settings.mem0_api_key
        if not api_key:
            raise ValueError(
                "Mem0 API key not configured. "
                "Set it via 'tribal init' or TRIBAL_MEM0_API_KEY environment variable."
            )

        # Mem0 SDK requires both org_id and project_id, or neither.
        org_id = settings.mem0_org_id or None
        project_id = settings.mem0_project_id or None
        if bool(org_id) != bool(project_id):
            raise ValueError(
                "Mem0 requires both org_id and project_id, or neither. "
                "Set both via 'tribal init' or TRIBAL_MEM0_ORG_ID / TRIBAL_MEM0_PROJECT_ID."
            )

        return Mem0Provider(
            api_key=api_key,
            org_id=org_id,
            project_id=project_id,
            user_id=settings.project_assistant_id or "tribalmind",
        )

    _REGISTRY["backboard"] = ("Backboard (default — hosted, team-shared)", _build_backboard, False)
    _REGISTRY["mem0"] = ("Mem0 (graph memory, managed)", _build_mem0, False)


# Initialize on import
_register_builtin_providers()


def get_provider_choices() -> list[tuple[str, str, bool]]:
    """Return list of (label, name, coming_soon) for provider selection UI."""
    return [
        (label, name, coming_soon)
        for name, (label, _, coming_soon) in _REGISTRY.items()
    ]


def get_provider(provider_name: str | None = None) -> MemoryProvider:
    """Create and return a configured MemoryProvider instance.

    If provider_name is None, reads from settings (which checks env vars and config).
    Defaults to 'backboard' if nothing is configured.
    """
    from tribalmind.config.settings import get_settings

    settings = get_settings()

    if provider_name is None:
        provider_name = settings.provider

    if provider_name not in _REGISTRY:
        available = ", ".join(_REGISTRY.keys())
        raise ValueError(
            f"Unknown memory provider: {provider_name!r}. "
            f"Available providers: {available}"
        )

    _, builder, coming_soon = _REGISTRY[provider_name]
    if coming_soon:
        raise ValueError(
            f"The {provider_name!r} provider is not yet available (coming soon)."
        )

    return builder(settings)


def register_provider(
    name: str,
    label: str,
    builder,
    *,
    coming_soon: bool = False,
) -> None:
    """Register a custom memory provider.

    Args:
        name: Short identifier (e.g. 'pinecone')
        label: Human-readable label for the init prompt
        builder: Callable that receives TribalSettings and returns a MemoryProvider
        coming_soon: If True, provider appears in selection but can't be used yet
    """
    _REGISTRY[name] = (label, builder, coming_soon)
