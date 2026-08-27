"""Tests for MoodFeed Live Activity, Online Community, and Notifications."""

import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_get_live_activity() -> None:
    res = client.get("/v1/activity")
    assert res.status_code == 200
    data = res.json()
    assert "activities" in data
    assert data["count"] > 0
    first_item = data["activities"][0]
    assert "user" in first_item
    assert "action" in first_item
    assert "text" in first_item
    assert "time" in first_item


def test_get_online_users() -> None:
    res = client.get("/v1/online")
    assert res.status_code == 200
    data = res.json()
    assert "online_count" in data
    assert data["online_count"] > 10000
    assert "users" in data
    assert len(data["users"]) > 0
    assert "summary_text" in data


def test_get_notifications() -> None:
    res = client.get("/v1/notifications")
    assert res.status_code == 200
    data = res.json()
    assert "notifications" in data
    assert data["unread_count"] >= 1
    notifs = data["notifications"]
    types = {n["type"] for n in notifs}
    assert "like" in types or "follow" in types
