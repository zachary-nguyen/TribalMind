"""Pluggable memory provider abstraction.

Providers implement the MemoryProvider protocol and are registered in the factory.
"""

from tribalmind.providers.base import MemoryProvider
from tribalmind.providers.factory import get_provider, get_provider_choices

__all__ = ["MemoryProvider", "get_provider", "get_provider_choices"]
