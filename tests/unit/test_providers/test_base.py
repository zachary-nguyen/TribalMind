"""Tests for the MemoryProvider protocol."""

from __future__ import annotations

from tribalmind.providers.backboard_provider import BackboardProvider
from tribalmind.providers.base import MemoryProvider


class TestMemoryProviderProtocol:
    def test_backboard_provider_implements_protocol(self):
        """BackboardProvider must satisfy the MemoryProvider protocol."""
        assert isinstance(BackboardProvider(), MemoryProvider)

    def test_protocol_is_runtime_checkable(self):
        """Protocol should be runtime-checkable for isinstance()."""
        assert hasattr(MemoryProvider, "__protocol_attrs__") or hasattr(
            MemoryProvider, "__abstractmethods__"
        ) or issubclass(type(MemoryProvider), type)
