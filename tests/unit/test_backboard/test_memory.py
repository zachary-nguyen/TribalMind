"""Tests for Backboard memory encoding/decoding."""

from __future__ import annotations

import pytest

from tribalmind.backboard.memory import encode_memory, parse_memory


class TestEncodeMemory:
    def test_encode_error(self):
        result = encode_memory(
            "error",
            package="requests",
            version="2.31",
            error_text="ConnectionError: timeout",
            fix_text="increase timeout to 30s",
            confidence=0.85,
        )
        assert "[error]" in result
        assert "package=requests" in result
        assert "version=2.31" in result
        assert "ConnectionError: timeout" in result
        assert "fix: increase timeout to 30s" in result
        assert "confidence=0.85" in result

    def test_encode_minimal(self):
        result = encode_memory("context", extra="general context info")
        assert "[context]" in result
        assert "general context info" in result


class TestParseMemory:
    def test_parse_full_entry(self):
        content = "[error] package=requests version=2.31 | ConnectionError: timeout | fix: increase timeout | confidence=0.85 trust=0.90"
        entry = parse_memory(content)
        assert entry.category == "error"
        assert entry.package == "requests"
        assert entry.version == "2.31"
        assert entry.error_text == "ConnectionError: timeout"
        assert entry.fix_text == "increase timeout"
        assert entry.confidence == 0.85
        assert entry.trust_score == 0.90

    def test_parse_with_raw_metadata(self):
        content = "[fix] package=numpy | ImportError | fix: pip install numpy | confidence=0.95"
        raw = {"id": "mem-123", "score": 0.88}
        entry = parse_memory(content, raw=raw)
        assert entry.memory_id == "mem-123"
        assert entry.relevance_score == 0.88
        assert entry.package == "numpy"

    def test_parse_no_fix(self):
        content = "[error] package=flask | 500 Internal Server Error |"
        entry = parse_memory(content)
        assert entry.category == "error"
        assert entry.package == "flask"
        assert entry.fix_text == ""

    def test_roundtrip(self):
        encoded = encode_memory(
            "error",
            package="httpx",
            error_text="ConnectError",
            fix_text="check network",
            confidence=0.75,
        )
        parsed = parse_memory(encoded)
        assert parsed.category == "error"
        assert parsed.package == "httpx"
        assert parsed.fix_text == "check network"
        assert parsed.confidence == 0.75
