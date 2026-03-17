"""Tests for the /api/activity endpoints."""

from __future__ import annotations

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from tribalmind.web.server import app

client = TestClient(app)

SAMPLE_EVENTS = [
    {"timestamp": "2026-03-17T10:00:00+00:00", "action": "remember", "summary": "stored a fix", "count": 1},
    {"timestamp": "2026-03-17T09:00:00+00:00", "action": "recall", "summary": "searched for auth", "count": 3},
    {"timestamp": "2026-03-17T08:00:00+00:00", "action": "forget", "summary": "deleted stale", "count": 1},
    {"timestamp": "2026-03-17T07:00:00+00:00", "action": "recall", "summary": "searched for db", "count": 5},
]


@patch("tribalmind.activity.read_activity", return_value=SAMPLE_EVENTS)
def test_get_activity_unfiltered(mock_read):
    resp = client.get("/api/activity")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 4
    mock_read.assert_called_once_with(limit=100, offset=0)


@patch("tribalmind.activity.read_activity", return_value=SAMPLE_EVENTS)
def test_get_activity_filter_by_action(mock_read):
    resp = client.get("/api/activity?action=recall")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert all(e["action"] == "recall" for e in data)


@patch("tribalmind.activity.read_activity", return_value=SAMPLE_EVENTS)
def test_get_activity_filter_no_match(mock_read):
    resp = client.get("/api/activity?action=nonexistent")
    assert resp.status_code == 200
    assert resp.json() == []


@patch("tribalmind.activity.clear_activity", return_value=42)
def test_delete_activity(mock_clear):
    resp = client.delete("/api/activity")
    assert resp.status_code == 200
    assert resp.json() == {"deleted": 42}
    mock_clear.assert_called_once()
