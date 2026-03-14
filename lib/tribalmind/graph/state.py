"""LangGraph state definitions for the TribalMind agent.

The TribalState TypedDict is the contract between all graph nodes.
"""

from __future__ import annotations

import operator
from dataclasses import dataclass, field
from typing import Annotated, Any, TypedDict


@dataclass
class ShellEvent:
    """A captured shell command execution from the shell hook."""

    command: str
    exit_code: int
    cwd: str
    timestamp: float
    stderr: str = ""
    stdout_tail: str = ""
    shell: str = ""


@dataclass
class ContextResult:
    """Results from multi-hop context search."""

    local_matches: list[Any] = field(default_factory=list)
    team_matches: list[Any] = field(default_factory=list)
    upstream_info: dict[str, Any] | None = None

    @property
    def has_matches(self) -> bool:
        return bool(self.local_matches or self.team_matches or self.upstream_info)


class TribalState(TypedDict, total=False):
    """State passed between LangGraph nodes.

    Uses total=False so nodes only need to return the fields they update.
    """

    # Input from shell hook
    event: ShellEvent

    # Monitor node output
    is_error: bool
    error_signature: str
    error_package: str | None
    error_type: str | None

    # Context node output
    context: ContextResult | None
    has_known_fix: bool

    # Inference node output
    suggested_fix: str | None
    fix_confidence: float

    # Promotion node output
    promoted: bool

    # UI node output
    displayed: bool
    rendered_insight: str | None

    # Accumulated log (uses reducer to append across nodes)
    log: Annotated[list[str], operator.add]
