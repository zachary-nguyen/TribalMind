"""IPC client for communicating with the TribalMind daemon.

Used by shell hooks (via a lightweight subprocess) and CLI commands.
"""

from __future__ import annotations

import asyncio
import logging

from tribalmind.config.settings import get_settings
from tribalmind.daemon.protocol import DaemonMessage

logger = logging.getLogger(__name__)


async def send_message(
    msg: DaemonMessage,
    host: str | None = None,
    port: int | None = None,
    timeout: float = 5.0,
) -> DaemonMessage | None:
    """Send a message to the daemon and optionally receive a response."""
    settings = get_settings()
    host = host or settings.daemon_host
    port = port or settings.daemon_port

    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port),
            timeout=timeout,
        )
    except (TimeoutError, ConnectionRefusedError, OSError):
        return None

    try:
        writer.write(msg.serialize())
        await writer.drain()

        # Read response if available
        try:
            data = await asyncio.wait_for(reader.readline(), timeout=timeout)
            if data:
                return DaemonMessage.deserialize(data)
        except TimeoutError:
            pass

        return None
    finally:
        writer.close()
        try:
            await writer.wait_closed()
        except Exception:
            pass


async def send_shell_event(
    command: str,
    exit_code: int,
    cwd: str,
    timestamp: float,
    stderr: str = "",
    shell: str = "",
) -> None:
    """Send a shell event to the daemon (fire-and-forget)."""
    msg = DaemonMessage.shell_event(
        command=command,
        exit_code=exit_code,
        cwd=cwd,
        timestamp=timestamp,
        stderr=stderr,
        shell=shell,
    )
    await send_message(msg, timeout=2.0)


async def ping_daemon(
    host: str | None = None,
    port: int | None = None,
) -> bool:
    """Check if the daemon is alive and responding."""
    response = await send_message(
        DaemonMessage.status_request(),
        host=host,
        port=port,
        timeout=2.0,
    )
    if response and response.type == "status_response":
        return response.payload.get("running", False)
    return False


async def shutdown_daemon(
    host: str | None = None,
    port: int | None = None,
) -> bool:
    """Send a shutdown command to the daemon."""
    response = await send_message(
        DaemonMessage.shutdown(),
        host=host,
        port=port,
        timeout=5.0,
    )
    return response is not None
