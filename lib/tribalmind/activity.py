"""Local activity log for tracking memory interactions.

Appends JSON-lines to a file in the user data directory. Each line is one event
(remember, recall, forget) with timestamp, action, summary, and metadata.

The log is append-only and local — it never leaves the machine.
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def _log_path() -> Path:
    """Return the path to the activity log file, creating parent dirs if needed."""
    from tribalmind.config.settings import get_settings

    data_dir = get_settings().data_dir
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / "activity.jsonl"


def log_activity(
    action: str,
    summary: str,
    *,
    query: str = "",
    memory_id: str = "",
    count: int = 0,
    source: str = "",
    assistant_id: str = "",
    metadata: dict[str, Any] | None = None,
) -> None:
    """Append an activity event to the local log.

    Parameters
    ----------
    action : str
        One of "remember", "recall", "forget".
    summary : str
        Human-readable summary of what happened.
    query : str
        The query or input text (for recall/remember).
    memory_id : str
        Specific memory ID affected (for forget --id).
    count : int
        Number of results returned (recall) or memories deleted (forget).
    source : str
        Where the command came from (e.g. "cli", "agent").
    assistant_id : str
        Backboard assistant ID the action targeted.
    metadata : dict
        Any additional context to log.
    """
    event = {
        "timestamp": datetime.now(UTC).isoformat(),
        "action": action,
        "summary": summary,
        "query": query,
        "memory_id": memory_id,
        "count": count,
        "source": source,
        "assistant_id": assistant_id,
        **(metadata or {}),
    }
    try:
        with open(_log_path(), "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except OSError:
        pass  # Never fail the command because of logging


def read_activity(limit: int = 100, offset: int = 0) -> list[dict]:
    """Read the most recent activity events (newest first).

    Parameters
    ----------
    limit : int
        Maximum number of events to return.
    offset : int
        Number of events to skip from the newest end.

    Returns
    -------
    list[dict]
        Events in reverse chronological order.
    """
    path = _log_path()
    if not path.exists():
        return []

    # Read all lines, reverse, then slice — fine for reasonable log sizes.
    # For very large logs we'd use a seek-from-end approach.
    lines: list[str] = []
    try:
        with open(path, encoding="utf-8") as f:
            lines = f.readlines()
    except OSError:
        return []

    lines.reverse()
    selected = lines[offset : offset + limit]

    events: list[dict] = []
    for line in selected:
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue

    return events


def clear_activity() -> int:
    """Delete the activity log. Returns the number of events deleted."""
    path = _log_path()
    if not path.exists():
        return 0
    try:
        count = sum(1 for line in open(path, encoding="utf-8") if line.strip())
        os.remove(path)
        return count
    except OSError:
        return 0
