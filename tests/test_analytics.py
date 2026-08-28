"""Tests for User Analytics and Export endpoints."""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_analytics_dashboard_metrics() -> None:
    res = client.get("/v1/analytics/dashboard")
    assert res.status_code == 200
    data = res.json()
    assert "stats" in data
    assert "mood_trends_7d" in data
    assert "engagement_30d" in data
    assert len(data["mood_trends_7d"]) == 7


def test_analytics_csv_export() -> None:
    res = client.get("/v1/analytics/export?format=csv")
    assert res.status_code == 200
    assert res.headers["content-type"].startswith("text/csv")
    assert "Mood Label" in res.text
