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


class TribalDaemon:
    """Background daemon that processes shell events through the LangGraph agent."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._server: asyncio.Server | None = None
        self._graph = None  # Lazy-loaded to avoid import cost at startup

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
                await self._handle_shell_event(msg)

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

        except asyncio.TimeoutError:
            logger.warning("Connection from %s timed out", addr)
        except Exception:
            logger.exception("Error handling connection from %s", addr)
        finally:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

    async def _handle_shell_event(self, msg: DaemonMessage) -> None:
        """Process a shell event through the LangGraph state machine."""
        payload = msg.payload

        # Check ignore list
        command = payload.get("command", "")
        base_cmd = command.split()[0] if command else ""
        if base_cmd in self._settings.ignore_commands:
            logger.debug("Ignoring command: %s", base_cmd)
            return

        # Check watch directories — if none configured, ignore everything
        if not self._settings.watch_dirs:
            logger.debug("No watch_dirs configured, skipping command")
            return
        cwd = Path(payload.get("cwd", ""))
        if not any(
            cwd == d or cwd.is_relative_to(d)
            for d in self._settings.watch_dirs
        ):
            logger.debug("Skipping command outside watched dirs: %s", cwd)
            return

        event = ShellEvent(
            command=command,
            exit_code=payload.get("exit_code", 0),
            cwd=payload.get("cwd", ""),
            timestamp=payload.get("timestamp", 0),
            stderr=payload.get("stderr", ""),
            shell=payload.get("shell", ""),
        )

        graph = self._get_graph()
        try:
            result = await graph.ainvoke({"event": event})
            log_entries = result.get("log", [])
            for entry in log_entries:
                logger.info("graph: %s", entry)
        except Exception:
            logger.exception("Error processing shell event: %s", command[:80])

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

    # Console handler (used in foreground mode)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(fmt)

    # File handler (always on — enables UI log streaming)
    settings = get_settings()
    log_file = settings.log_file
    log_file.parent.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(fmt)

    logging.basicConfig(level=logging.INFO, handlers=[console_handler, file_handler])

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
