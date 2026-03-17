"""Tests for Backboard memory encoding/decoding."""

from __future__ import annotations

import json

import pytest
from tribalmind.backboard.memory import MEMORY_SCHEMA, encode_memory, parse_memory


class TestMemorySchema:
    def test_schema_has_required_fields(self):
        assert "category" in MEMORY_SCHEMA
        assert "subject" in MEMORY_SCHEMA
        assert "content" in MEMORY_SCHEMA

    def test_schema_has_no_legacy_fields(self):
        assert "package" not in MEMORY_SCHEMA
        assert "fix_text" not in MEMORY_SCHEMA
        assert "error_text" not in MEMORY_SCHEMA
        assert "confidence" not in MEMORY_SCHEMA


class TestEncodeMemory:
    def test_encode_fix(self):
        result = encode_memory(
            "fix",
            subject="requests timeout",
            content="increase timeout to 30s when hitting the payments API",
        )
        data = json.loads(result)
        assert data["category"] == "fix"
        assert data["subject"] == "requests timeout"
        assert data["content"] == "increase timeout to 30s when hitting the payments API"

    def test_encode_minimal(self):
        result = encode_memory("context")
        data = json.loads(result)
        assert data["category"] == "context"
        assert data["subject"] == ""
        assert data["content"] == ""

    def test_encode_produces_valid_json(self):
        result = encode_memory("tip", subject="debugging", content="use --verbose")
        data = json.loads(result)
        assert isinstance(data, dict)

    def test_encode_architecture(self):
        result = encode_memory(
            "architecture",
            subject="auth module",
            content="JWT tokens are validated in middleware before reaching handlers",
        )
        data = json.loads(result)
        assert data["category"] == "architecture"


class TestParseMemory:
    def test_parse_json_entry(self):
        content = json.dumps({
            "category": "fix",
            "subject": "requests timeout",
            "content": "increase timeout to 30s",
        })
        entry = parse_memory(content)
        assert entry.category == "fix"
        assert entry.subject == "requests timeout"
        assert entry.content == "increase timeout to 30s"

    def test_parse_with_raw_metadata(self):
        content = json.dumps({
            "category": "convention",
            "subject": "API routes",
            "content": "all routes follow /api/v2/{resource} pattern",
        })
        raw = {"id": "mem-123", "score": 0.88}
        entry = parse_memory(content, raw=raw)
        assert entry.memory_id == "mem-123"
        # score is a distance; relevance = 1 - distance
        assert entry.relevance_score == pytest.approx(0.12)
        assert entry.subject == "API routes"

    def test_parse_legacy_json_format(self):
        """Old JSON format with fix_text/package should migrate."""
        content = json.dumps({
            "category": "fix",
            "package": "numpy",
            "fix_text": "pin to <1.26",
        })
        entry = parse_memory(content)
        assert entry.category == "fix"
        assert entry.subject == "numpy"
        assert entry.content == "pin to <1.26"

    def test_parse_legacy_pipe_format(self):
        """Old pipe-delimited format should still parse."""
        content = "[error] package=flask | 500 Internal Server Error |"
        entry = parse_memory(content)
        assert entry.category == "error"
        assert entry.subject == "flask"

    def test_roundtrip(self):
        encoded = encode_memory(
            "decision",
            subject="database choice",
            content="chose Postgres over SQLite for concurrent write support",
        )
        parsed = parse_memory(encoded)
        assert parsed.category == "decision"
        assert parsed.subject == "database choice"
        assert parsed.content == "chose Postgres over SQLite for concurrent write support"
