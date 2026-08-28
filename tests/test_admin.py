"""Tests for Admin Dashboard, Moderation Queue, and Feature Flags."""

import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_admin_kpi_stats() -> None:
    res = client.get("/v1/admin/stats")
    assert res.status_code == 200
    data = res.json()
    assert "dau" in data
    assert "mau" in data
    assert "mrr_revenue" in data


def test_admin_users_and_verification() -> None:
    uid = uuid.uuid4().hex[:8]
    reg = client.post("/v1/register", json={
        "email": f"admin.target.{uid}@moodfeed.app",
        "password": "Password123!",
        "username": f"adm_target_{uid}",
        "display_name": "Target User",
    })
    user_id = reg.json()["user"]["id"]

    # Verify user
    v_res = client.post(f"/v1/admin/users/{user_id}/verify")
    assert v_res.status_code == 200
    assert v_res.json()["is_verified"] is True

    # List users
    list_res = client.get("/v1/admin/users")
    assert list_res.status_code == 200
    assert list_res.json()["count"] >= 1


def test_admin_feature_flags() -> None:
    res = client.get("/v1/admin/flags")
    assert res.status_code == 200
    flags = res.json()["flags"]
    assert "enable_stripe_monetization" in flags

    # Toggle flag
    toggle_res = client.post("/v1/admin/flags", json={"flag_name": "enable_dark_mode_v2", "enabled": False})
    assert toggle_res.status_code == 200
    assert toggle_res.json()["flags"]["enable_dark_mode_v2"] is False


def test_admin_system_health() -> None:
    res = client.get("/v1/admin/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "database" in data["services"]
