"""Daemon process lifecycle management.

Handles starting/stopping the daemon as a background process,
PID file management, and cross-platform process control.
"""

from __future__ import annotations

import asyncio
import logging
import os
import signal
import subprocess
import sys
from pathlib import Path

from tribalmind.config.settings import get_settings

logger = logging.getLogger(__name__)


def _get_pid_file() -> Path:
    """Get the path to the daemon PID file."""
    settings = get_settings()
    return settings.pid_file


def _get_creation_flags() -> int:
    """Get platform-specific subprocess creation flags for detached processes."""
    if sys.platform == "win32":
        return subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
    return 0


def read_pid() -> int | None:
    """Read the daemon PID from the PID file."""
    pid_file = _get_pid_file()
    if not pid_file.exists():
        return None
    try:
        pid = int(pid_file.read_text().strip())
        return pid
    except (ValueError, OSError):
        return None


def _process_alive(pid: int) -> bool:
    """Check if a process with the given PID is alive."""
    try:
        if sys.platform == "win32":
            # On Windows, os.kill with signal 0 doesn't work the same way
            import ctypes
            kernel32 = ctypes.windll.kernel32
            handle = kernel32.OpenProcess(0x1000, False, pid)  # PROCESS_QUERY_LIMITED_INFORMATION
            if handle:
                kernel32.CloseHandle(handle)
                return True
            return False
        else:
            os.kill(pid, 0)
            return True
    except (OSError, ProcessLookupError):
        return False


def is_running() -> bool:
    """Check if the daemon is currently running."""
    pid = read_pid()
    if pid is None:
        return False
    if not _process_alive(pid):
        # Stale PID file - clean up
        try:
            _get_pid_file().unlink()
        except OSError:
            pass
        return False
    return True


def start_daemon() -> None:
    """Launch the daemon as a background process."""
    if is_running():
        logger.warning("Daemon is already running")
        return

    pid_file = _get_pid_file()
    pid_file.parent.mkdir(parents=True, exist_ok=True)

    # Launch as a detached subprocess
    proc = subprocess.Popen(
        [sys.executable, "-m", "tribalmind.daemon.server"],
        creationflags=_get_creation_flags(),
        start_new_session=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )

    pid_file.write_text(str(proc.pid))
    logger.info("Daemon started with PID %d", proc.pid)


def start_foreground() -> None:
    """Run the daemon in the foreground (for debugging)."""
    from tribalmind.daemon.server import run_daemon
    run_daemon()


def stop_daemon() -> None:
    """Stop the daemon process."""
    pid = read_pid()
    if pid is None:
        logger.warning("No PID file found")
        return

    # Try graceful shutdown via IPC first
    try:
        from tribalmind.daemon.client import shutdown_daemon
        success = asyncio.run(shutdown_daemon())
        if success:
            logger.info("Daemon shut down gracefully")
            _cleanup_pid_file()
            return
    except Exception:
        pass

    # Fallback: kill the process
    try:
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
            )
        else:
            os.kill(pid, signal.SIGTERM)
        logger.info("Daemon process %d terminated", pid)
    except (OSError, ProcessLookupError):
        logger.warning("Process %d not found", pid)

    _cleanup_pid_file()


def _cleanup_pid_file() -> None:
    """Remove the PID file."""
    try:
        _get_pid_file().unlink(missing_ok=True)
    except OSError:
        pass
