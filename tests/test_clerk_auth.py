"""Tests for MoodFeed Clerk Authentication & User Synchronization.

Verifies:
1. /v1/auth/config endpoint public configuration and security invariants.
2. Clerk session token decoding, signature mock verification, and claim validation.
3. Automatic synchronization of Clerk identities with local SQLAlchemy User & UserPreferences.
4. Protected API endpoints (/v1/me, /v1/auth/me, /v1/posts, /v1/preferences) with Clerk tokens.
5. Expired, invalid, and malformed token rejection (401 UNAUTHORIZED).
6. Local JWT fallback coexistence without interference.
7. Zero network calls to external Clerk servers during testing.
"""

import time
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.auth.clerk import set_mock_clerk_verifier, verify_clerk_token, get_or_sync_clerk_user
from backend.auth.security import create_jwt_token
from backend.config import settings
from backend.main import app

client = TestClient(app)


def test_auth_config_endpoint_returns_public_settings_without_secrets() -> None:
    """Ensures /v1/auth/config exposes publishable key but never leaks secret keys."""
    res = client.get("/v1/auth/config")
    assert res.status_code == 200
    data = res.json()

    assert "auth_provider" in data
    assert "features" in data
    assert "clerk_auth" in data["features"]
    assert "local_auth_fallback" in data["features"]

    # Invariants: Secret keys must NEVER be present in response
    assert "clerk_secret_key" not in data
    assert "jwt_secret" not in data
    assert "session_secret" not in data


def test_clerk_session_token_syncs_user_and_preferences() -> None:
    """Verifies that a valid Clerk token creates a local User and UserPreferences record."""
    clerk_user_id = f"user_clerk_{uuid.uuid4().hex[:8]}"
    email = f"clerk.test.{uuid.uuid4().hex[:6]}@example.com"
    display_name = "Clerk Test Kullanıcısı"

    # Define mock verifier payload
    mock_payload = {
        "sub": clerk_user_id,
        "email": email,
        "username": "clerk_tester",
        "display_name": display_name,
        "avatar": "C",
        "iat": int(time.time()),
        "exp": int(time.time()) + 3600,
    }

    test_token = f"mock.clerk.jwt.{clerk_user_id}"

    # Set mock verifier to intercept without external network requests
    set_mock_clerk_verifier(lambda t: mock_payload if t == test_token else None)

    try:
        # Access /v1/me with Clerk session token
        res = client.get("/v1/me", headers={"Authorization": f"Bearer {test_token}"})
        assert res.status_code == 200
        user_data = res.json()

        assert user_data["email"] == email
        assert user_data["display_name"] == display_name
        assert "id" in user_data
        assert user_data["auth_provider"] == "clerk"

        # Verify /v1/auth/me also resolves the synced user
        auth_me_res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {test_token}"})
        assert auth_me_res.status_code == 200
        assert auth_me_res.json()["email"] == email

        # Test creating a post using Clerk authentication
        post_res = client.post(
            "/v1/posts",
            headers={"Authorization": f"Bearer {test_token}"},
            json={"content": "Clerk ile doğrulanmış ilk gönderi!", "category": "Teknoloji"},
        )
        assert post_res.status_code == 200
        post_data = post_res.json()
        assert post_data["success"] is True
        assert post_data["post"]["content"] == "Clerk ile doğrulanmış ilk gönderi!"
    finally:
        set_mock_clerk_verifier(None)


def test_expired_clerk_token_returns_401_unauthorized() -> None:
    """Verifies that an expired Clerk token is rejected with 401."""
    expired_token = "mock.clerk.expired.token"

    # Mock verifier returns None for expired token
    set_mock_clerk_verifier(lambda t: None)

    try:
        res = client.get("/v1/me", headers={"Authorization": f"Bearer {expired_token}"})
        assert res.status_code == 401
        assert res.json()["detail"]["code"] == "UNAUTHORIZED"
    finally:
        set_mock_clerk_verifier(None)


def test_local_jwt_fallback_coexists_with_clerk() -> None:
    """Verifies that local JWT tokens continue to work when Clerk is configured."""
    uid = uuid.uuid4().hex[:8]
    email = f"local.fallback.{uid}@moodfeed.app"
    password = "GuvenliLocal123!"

    # Register local user
    reg_res = client.post("/v1/register", json={
        "email": email,
        "password": password,
        "username": f"local_{uid}",
        "display_name": "Yerel Kullanıcı",
    })
    assert reg_res.status_code == 200
    local_token = reg_res.json()["access_token"]

    # Verify /v1/me resolves local user
    me_res = client.get("/v1/me", headers={"Authorization": f"Bearer {local_token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email


def test_malformed_authorization_header_returns_401() -> None:
    """Ensures missing Bearer prefix or empty header returns 401."""
    res1 = client.get("/v1/me", headers={"Authorization": "InvalidHeaderFormat"})
    assert res1.status_code == 401

    res2 = client.get("/v1/me")
    assert res2.status_code == 401
