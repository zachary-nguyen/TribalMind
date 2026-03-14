"""Tests for the daemon IPC protocol."""

from __future__ import annotations

from tribalmind.daemon.protocol import DaemonMessage


class TestDaemonMessage:
    def test_serialize_deserialize_roundtrip(self):
        msg = DaemonMessage(type="test", payload={"key": "value"})
        data = msg.serialize()
        restored = DaemonMessage.deserialize(data)
        assert restored.type == "test"
        assert restored.payload == {"key": "value"}

    def test_shell_event_factory(self):
        msg = DaemonMessage.shell_event(
            command="pip install requests",
            exit_code=0,
            cwd="/home/user",
            timestamp=1710000000.0,
            stderr="",
            shell="bash",
        )
        assert msg.type == "shell_event"
        assert msg.payload["command"] == "pip install requests"
        assert msg.payload["exit_code"] == 0

    def test_status_request_factory(self):
        msg = DaemonMessage.status_request()
        assert msg.type == "status_request"
        assert msg.payload == {}

    def test_status_response_factory(self):
        msg = DaemonMessage.status_response(running=True, uptime=3600)
        assert msg.type == "status_response"
        assert msg.payload["running"] is True
        assert msg.payload["uptime"] == 3600

    def test_shutdown_factory(self):
        msg = DaemonMessage.shutdown()
        assert msg.type == "shutdown"

    def test_serialize_ends_with_newline(self):
        msg = DaemonMessage(type="test", payload={})
        data = msg.serialize()
        assert data.endswith(b"\n")

    def test_deserialize_strips_whitespace(self):
        raw = b'{"type": "test", "payload": {}}\n\n'
        msg = DaemonMessage.deserialize(raw)
        assert msg.type == "test"
