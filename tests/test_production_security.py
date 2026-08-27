"""Production Security & ASVS Compliance Tests."""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_unauthenticated_endpoints_return_structured_401() -> None:
    endpoints = [
        ("GET", "/v1/auth/me"),
        ("GET", "/v1/preferences"),
        ("PATCH", "/v1/preferences"),
        ("GET", "/v1/saved"),
        ("POST", "/v1/saved"),
        ("GET", "/v1/muted"),
        ("POST", "/v1/feedback"),
        ("POST", "/v1/privacy/data/export"),
        ("POST", "/v1/privacy/data/deletion"),
    ]
    for method, path in endpoints:
        if method == "GET":
            res = client.get(path)
        elif method == "PATCH":
            res = client.patch(path, json={})
        elif method == "POST":
            res = client.post(path, json={})
        assert res.status_code == 401
        data = res.json()["detail"]
        assert data["code"] == "UNAUTHORIZED"
        assert "request_id" in data


def test_idor_cross_user_isolation() -> None:
    # Register user A
    res_a = client.post("/v1/auth/register", json={"email": "user.a@moodfeed.app", "password": "Password123!", "display_name": "User A"})
    token_a = res_a.json()["access_token"]

    # Register user B
    res_b = client.post("/v1/auth/register", json={"email": "user.b@moodfeed.app", "password": "Password123!", "display_name": "User B"})
    token_b = res_b.json()["access_token"]

    # User A saves an item
    client.post("/v1/saved", json={"content_id": "post-secret-a"}, headers={"Authorization": f"Bearer {token_a}"})

    # User B lists saved items -> MUST NOT see User A's item
    saved_b = client.get("/v1/saved", headers={"Authorization": f"Bearer {token_b}"}).json()["saved_ids"]
    assert "post-secret-a" not in saved_b


def test_sql_injection_payload_resilience() -> None:
    payload = "' OR 1=1 --"
    res = client.post("/v1/auth/login", json={"email": payload, "password": "password"})
    assert res.status_code == 422 or res.status_code == 401


def test_xss_in_notes_sanitized() -> None:
    reg = client.post("/v1/auth/register", json={"email": "xss.user@moodfeed.app", "password": "Password123!", "display_name": "XSS User"})
    token = reg.json()["access_token"]

    res = client.post("/v1/feedback", json={
        "content_id": "post-001",
        "action": "helpful",
        "note": "<script>alert('pwned')</script>Harika bir sistem.",
    }, headers={"Authorization": f"Bearer {token}"})
    assert res.status_code == 200
    assert "<script>" not in res.json()["note"]
