"""JSON-line IPC protocol for daemon communication.

Messages are single-line JSON objects terminated by newline.
Types: shell_event, status_request, status_response, shutdown, config_reload.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any


@dataclass
class DaemonMessage:
    """A message exchanged between the shell hook/CLI and the daemon."""

    type: str
    payload: dict[str, Any] = field(default_factory=dict)

    def serialize(self) -> bytes:
        """Serialize to a JSON line (bytes)."""
        return json.dumps({"type": self.type, "payload": self.payload}).encode("utf-8") + b"\n"

    @classmethod
    def deserialize(cls, data: bytes) -> DaemonMessage:
        """Deserialize a JSON line into a DaemonMessage."""
        parsed = json.loads(data.strip())
        return cls(type=parsed["type"], payload=parsed.get("payload", {}))

    # Convenience constructors
    @classmethod
    def shell_event(
        cls,
        command: str,
        exit_code: int,
        cwd: str,
        timestamp: float,
        stderr: str = "",
        shell: str = "",
    ) -> DaemonMessage:
        return cls(
            type="shell_event",
            payload={
                "command": command,
                "exit_code": exit_code,
                "cwd": cwd,
                "timestamp": timestamp,
                "stderr": stderr,
                "shell": shell,
            },
        )

    @classmethod
    def status_request(cls) -> DaemonMessage:
        return cls(type="status_request")

    @classmethod
    def status_response(cls, running: bool = True, **info: Any) -> DaemonMessage:
        return cls(type="status_response", payload={"running": running, **info})

    @classmethod
    def shutdown(cls) -> DaemonMessage:
        return cls(type="shutdown")

    @classmethod
    def config_reload(cls) -> DaemonMessage:
        return cls(type="config_reload")
