"""Production Observability & System Health Tests."""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_system_liveness_probe() -> None:
    res = client.get("/v1/system/liveness")
    assert res.status_code == 200
    assert res.json() == {"status": "alive"}


def test_system_readiness_probe() -> None:
    res = client.get("/v1/system/readiness")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ready"
    assert "database" in data
    assert "ml_scorer" in data


def test_system_metrics_endpoint() -> None:
    res = client.get("/v1/system/metrics")
    assert res.status_code == 200
    data = res.json()
    assert "registered_users" in data
    assert "active_sessions" in data
    assert "audit_events_logged" in data


def test_process_time_header_present() -> None:
    res = client.get("/v1/system/health")
    assert res.status_code == 200
    assert "X-Process-Time-Ms" in res.headers
    val = float(res.headers["X-Process-Time-Ms"])
    assert val >= 0.0
