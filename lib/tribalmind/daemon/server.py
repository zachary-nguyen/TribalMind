"""Asyncio TCP server for the TribalMind daemon.

Listens on localhost for shell events from hooks, processes them through
the LangGraph state machine, and returns results.
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from pathlib import Path

from tribalmind.config.settings import get_settings
from tribalmind.daemon.protocol import DaemonMessage
from tribalmind.graph.state import ShellEvent

logger = logging.getLogger(__name__)


class _PendingFix:
    """Tracks a suggested fix awaiting validation by a subsequent successful command."""

    __slots__ = ("memory_id", "error_signature", "cwd", "timestamp")

    def __init__(self, memory_id: str, error_signature: str, cwd: str, timestamp: float):
        self.memory_id = memory_id
        self.error_signature = error_signature
        self.cwd = cwd
        self.timestamp = timestamp


class _LastError:
    """Tracks the most recent error so we can learn from user-initiated fixes."""

    __slots__ = ("error_signature", "error_type", "error_package", "cwd", "timestamp")

    def __init__(
        self,
        error_signature: str,
        error_type: str,
        error_package: str,
        cwd: str,
        timestamp: float,
    ):
        self.error_signature = error_signature
        self.error_type = error_type
        self.error_package = error_package
        self.cwd = cwd
        self.timestamp = timestamp


class TribalDaemon:
    """Background daemon that processes shell events through the LangGraph agent."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._server: asyncio.Server | None = None
        self._graph = None  # Lazy-loaded to avoid import cost at startup
        self._pending_fix: _PendingFix | None = None
        self._last_error: _LastError | None = None

    def _get_graph(self):
        """Lazy-load the compiled LangGraph state machine."""
        if self._graph is None:
            from tribalmind.graph.builder import build_graph
            self._graph = build_graph()
        return self._graph

    async def handle_connection(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        """Handle a single IPC connection."""
        addr = writer.get_extra_info("peername")
        try:
            data = await asyncio.wait_for(reader.readline(), timeout=5.0)
            if not data:
                return

            msg = DaemonMessage.deserialize(data)
            logger.debug("Received %s from %s", msg.type, addr)

            if msg.type == "shell_event":
                insight = await self._handle_shell_event(msg)
                if insight:
                    response = DaemonMessage.insight_response(text=insight)
                    writer.write(response.serialize())
                    await writer.drain()

            elif msg.type == "status_request":
                response = DaemonMessage.status_response(running=True)
                writer.write(response.serialize())
                await writer.drain()

            elif msg.type == "shutdown":
                logger.info("Shutdown requested")
                response = DaemonMessage.status_response(running=False)
                writer.write(response.serialize())
                await writer.drain()
                if self._server:
                    self._server.close()

            elif msg.type == "config_reload":
                from tribalmind.config.settings import clear_settings_cache
                clear_settings_cache()
                self._settings = get_settings()
                logger.info("Configuration reloaded")

        except TimeoutError:
            logger.warning("Connection from %s timed out", addr)
        except Exception:
            logger.exception("Error handling connection from %s", addr)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_shell_event(self, msg: DaemonMessage) -> str | None:
        """Process a shell event through the LangGraph state machine.

        Returns the rendered insight text if one was generated, or None.
        """
        payload = msg.payload

        # Check ignore list
        command = payload.get("command", "")
        base_cmd = command.split()[0] if command else ""
        exit_code = payload.get("exit_code", 0)
        cwd = payload.get("cwd", "")
        logger.info("Command received: %s (exit=%s, cwd=%s)", base_cmd, exit_code, cwd)
        if base_cmd in self._settings.ignore_commands:
            logger.debug("Ignoring command: %s", base_cmd)
            return None

        # Check watch directories — if none configured, allow everything
        if self._settings.watch_dirs:
            cwd = Path(payload.get("cwd", "")).resolve()
            if not any(
                cwd == d.resolve() or cwd.is_relative_to(d.resolve())
                for d in self._settings.watch_dirs
            ):
                logger.debug("Skipping command outside watched dirs: %s", cwd)
                return None

        event = ShellEvent(
            command=command,
            exit_code=payload.get("exit_code", 0),
            cwd=payload.get("cwd", ""),
            timestamp=payload.get("timestamp", 0),
            stderr=payload.get("stderr", ""),
            shell=payload.get("shell", ""),
        )

        # On success: check if this validates a pending fix or is a user-discovered fix
        if event.exit_code == 0:
            if self._pending_fix:
                await self._validate_fix(event)
            elif self._last_error:
                await self._learn_user_fix(event)

        graph = self._get_graph()
        try:
            result = await graph.ainvoke({"event": event})
            log_entries = result.get("log", [])
            for entry in log_entries:
                logger.info("graph: %s", entry)

            # Track the error for user-fix learning
            if result.get("is_error") and result.get("error_signature"):
                self._last_error = _LastError(
                    error_signature=result["error_signature"],
                    error_type=result.get("error_type", ""),
                    error_package=result.get("error_package", ""),
                    cwd=event.cwd,
                    timestamp=event.timestamp,
                )

            # If the pipeline produced a fix, track it for validation
            if result.get("suggested_fix") and result.get("error_signature"):
                memory_log = next(
                    (e for e in log_entries if e.startswith("promotion: stored")), ""
                )
                # Extract memory ID from promotion log
                mem_id = ""
                if "memory=" in memory_log:
                    mem_id = memory_log.split("memory=")[1].split()[0]

                if mem_id:
                    self._pending_fix = _PendingFix(
                        memory_id=mem_id,
                        error_signature=result["error_signature"],
                        cwd=event.cwd,
                        timestamp=event.timestamp,
                    )
                    logger.info(
                        "Tracking fix for validation: memory=%s sig=%s",
                        mem_id, result["error_signature"][:16],
                    )

            return result.get("rendered_insight")
        except Exception:
            logger.exception("Error processing shell event: %s", command[:80])
            return None

    async def _validate_fix(self, event: ShellEvent) -> None:
        """Validate a pending fix: the user's next command succeeded."""
        pending = self._pending_fix
        if not pending:
            return

        # Only validate if in the same working directory and within 5 minutes
        elapsed = event.timestamp - pending.timestamp
        if pending.cwd != event.cwd or elapsed > 300:
            logger.debug(
                "Pending fix expired or different cwd (elapsed=%.0fs)", elapsed
            )
            self._pending_fix = None
            return

        self._pending_fix = None  # consume it

        logger.info(
            "Fix validated! Next command succeeded (memory=%s, elapsed=%.0fs)",
            pending.memory_id, elapsed,
        )

        # Increment trust on the memory
        try:
            from tribalmind.backboard.client import create_client
            from tribalmind.backboard.memory import encode_memory, parse_memory, update_memory
            from tribalmind.graph.promotion import TRUST_INCREMENT

            settings = get_settings()
            if not settings.project_assistant_id:
                return

            async with create_client() as client:
                # Fetch current memory state
                raw = await client.get(
                    f"/assistants/{settings.project_assistant_id}"
                    f"/memories/{pending.memory_id}"
                )
                entry = parse_memory(raw.get("content", ""), raw=raw)

                new_trust = entry.trust_score + TRUST_INCREMENT
                updated = encode_memory(
                    entry.category or "error",
                    package=entry.package,
                    version=entry.version,
                    error_text=entry.error_text,
                    fix_text=entry.fix_text,
                    confidence=min(entry.confidence + 0.1, 1.0),
                    trust_score=new_trust,
                )
                await update_memory(
                    client, settings.project_assistant_id,
                    pending.memory_id, updated,
                )
                logger.info(
                    "Trust updated: memory=%s trust=%.1f -> %.1f confidence=%.2f",
                    pending.memory_id, entry.trust_score, new_trust,
                    min(entry.confidence + 0.1, 1.0),
                )

        except Exception:
            logger.exception("Failed to update trust for memory %s", pending.memory_id)

    async def _learn_user_fix(self, event: ShellEvent) -> None:
        """Learn from a user-discovered fix: error was followed by a successful command.

        When the pipeline didn't suggest a fix (or the user ignored it), but they
        ran a command that succeeded — store that command as a potential fix.
        """
        last = self._last_error
        if not last:
            return

        # Same constraints: same cwd, within 5 minutes
        elapsed = event.timestamp - last.timestamp
        if last.cwd != event.cwd or elapsed > 300:
            self._last_error = None
            return

        self._last_error = None  # consume it

        # Skip trivial commands that aren't likely fixes
        cmd = event.command.strip()
        trivial = {"ls", "dir", "pwd", "cd", "cls", "clear", "echo", "cat", "type", "whoami"}
        first_word = cmd.split()[0].lower() if cmd else ""
        if first_word in trivial:
            return

        logger.info(
            "User-discovered fix: '%s' resolved %s (elapsed=%.0fs)",
            cmd[:80], last.error_type or last.error_signature[:16], elapsed,
        )

        try:
            from tribalmind.backboard.client import create_client
            from tribalmind.backboard.memory import (
                add_memory,
                encode_memory,
                search_memories,
            )

            settings = get_settings()
            if not settings.project_assistant_id:
                return

            async with create_client() as client:
                # Check if we already have a memory for this error
                existing = await search_memories(
                    client, settings.project_assistant_id,
                    last.error_signature, limit=3,
                )
                for entry in existing:
                    if entry.relevance_score > 0.9 and entry.fix_text:
                        logger.debug(
                            "Memory already exists for this error with a fix, skipping"
                        )
                        return

                # Store the user's command as a discovered fix
                content = encode_memory(
                    "error",
                    package=last.error_package,
                    error_text=last.error_signature,
                    fix_text=cmd,
                    confidence=0.5,  # lower confidence — observed, not verified multiple times
                    trust_score=1.0,
                    extra="source=user-observed",
                )
                result = await add_memory(
                    client, settings.project_assistant_id, content,
                )
                mem_id = result.get("memory_id", result.get("id", ""))
                logger.info(
                    "Stored user-discovered fix: memory=%s fix='%s'",
                    mem_id, cmd[:60],
                )

        except Exception:
            logger.exception("Failed to store user-discovered fix")

    async def start(self) -> None:
        """Start the TCP server and serve forever."""
        self._server = await asyncio.start_server(
            self.handle_connection,
            self._settings.daemon_host,
            self._settings.daemon_port,
        )
        addrs = ", ".join(str(s.getsockname()) for s in self._server.sockets)
        logger.info("TribalMind daemon listening on %s", addrs)

        async with self._server:
            await self._server.serve_forever()


def run_daemon() -> None:
    """Entry point for running the daemon (used by manager.py)."""
    fmt = logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Console handler (used in foreground mode) — force UTF-8 on Windows
    console_handler = logging.StreamHandler(
        open(sys.stdout.fileno(), mode="w", encoding="utf-8", closefd=False)
        if sys.platform == "win32" else sys.stderr
    )
    console_handler.setFormatter(fmt)

    # File handler (always on — enables UI log streaming) — force UTF-8
    settings = get_settings()
    log_file = settings.log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setFormatter(fmt)

    logging.basicConfig(level=logging.DEBUG, handlers=[console_handler, file_handler])

    daemon = TribalDaemon()

    # Handle graceful shutdown signals
    if sys.platform != "win32":
        loop = asyncio.new_event_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(sig, loop.stop)
        asyncio.set_event_loop(loop)

    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Daemon interrupted")
    except Exception:
        logger.exception("Daemon crashed")
        sys.exit(1)


if __name__ == "__main__":
    run_daemon()
