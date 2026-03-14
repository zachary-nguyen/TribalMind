"""CMD hook helper - sends shell events to the TribalMind daemon.

Called by cmd_wrapper.cmd after each command execution.
Handles TCP communication, spinner display, and insight rendering.

Usage: python -m tribalmind.hooks.cmd_send "<command>" <exit_code> "<cwd>"
"""

from __future__ import annotations

import json
import socket
import sys
import threading
import time

DAEMON_HOST = "127.0.0.1"
DAEMON_PORT = 7483
TIMEOUT_SUCCESS = 2.0
TIMEOUT_ERROR = 15.0

FRAMES = ["\u28f7", "\u28ef", "\u28df", "\u287f", "\u28bf", "\u28fb", "\u28fd", "\u28fe"]


def _show_spinner(stop_event: threading.Event) -> None:
    """Display a braille spinner until stop_event is set."""
    i = 0
    sys.stderr.write("\n  \033[36m" + FRAMES[0] + " TribalMind analyzing...\033[0m")
    sys.stderr.flush()
    while not stop_event.wait(0.08):
        i = (i + 1) % len(FRAMES)
        sys.stderr.write("\r  \033[36m" + FRAMES[i] + " TribalMind analyzing...\033[0m")
        sys.stderr.flush()
    # Clear spinner line
    sys.stderr.write("\r" + " " * 40 + "\r")
    sys.stderr.flush()


def send_event(command: str, exit_code: int, cwd: str) -> None:
    """Send a shell event to the daemon and display any insight response."""
    msg = json.dumps({
        "type": "shell_event",
        "payload": {
            "command": command,
            "exit_code": exit_code,
            "cwd": cwd,
            "timestamp": int(time.time()),
            "stderr": "",
            "shell": "cmd",
        },
    }) + "\n"

    timeout = TIMEOUT_ERROR if exit_code != 0 else TIMEOUT_SUCCESS

    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        sock.connect((DAEMON_HOST, DAEMON_PORT))
        sock.sendall(msg.encode("utf-8"))

        if exit_code == 0:
            # Fire-and-forget for successful commands
            sock.close()
            return

        # Show spinner while waiting for insight
        stop_spinner = threading.Event()
        spinner_thread = threading.Thread(target=_show_spinner, args=(stop_spinner,), daemon=True)
        spinner_thread.start()

        try:
            # Read response line
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk

            stop_spinner.set()
            spinner_thread.join(timeout=1)

            if buf.strip():
                resp = json.loads(buf.strip())
                text = resp.get("payload", {}).get("text", "")
                if text:
                    sys.stderr.write(text + "\n")
                    sys.stderr.flush()
        except (TimeoutError, json.JSONDecodeError):
            stop_spinner.set()
            spinner_thread.join(timeout=1)

        sock.close()

    except (OSError, ConnectionRefusedError):
        # Daemon not running — silently ignore
        pass


def main() -> None:
    if len(sys.argv) < 4:
        return

    command = sys.argv[1]
    try:
        exit_code = int(sys.argv[2])
    except ValueError:
        exit_code = 1
    cwd = sys.argv[3]

    send_event(command, exit_code, cwd)


if __name__ == "__main__":
    main()
