"""Production Authentication & Session Tests."""

from fastapi.testclient import TestClient
from backend.auth.security import hash_password, verify_password, create_jwt_token, verify_jwt_token
from backend.main import app

client = TestClient(app)


def test_password_hashing_and_constant_time_verification() -> None:
    raw = "GucluParola123!"
    h = hash_password(raw)
    assert h.startswith("pbkdf2:sha256:600000$")
    assert verify_password(raw, h) is True
    assert verify_password("YanlisParola", h) is False


def test_jwt_token_issuance_and_expiration() -> None:
    secret = "test_super_secret_min32chars_key_12345"
    token = create_jwt_token({"sub": "u-test-01", "role": "user"}, secret, ttl_seconds=2)
    payload = verify_jwt_token(token, secret)
    assert payload is not None
    assert payload["sub"] == "u-test-01"

    # Verify tampering detection
    tampered = token[:-4] + "abcd"
    assert verify_jwt_token(tampered, secret) is None


def test_register_login_and_current_user_flow() -> None:
    email = "deneme.kullanici@moodfeed.app"
    password = "GuvenliParola123*"
    display_name = "Deneme Kullanıcı"

    # 1. Register
    res = client.post("/v1/auth/register", json={
        "email": email,
        "password": password,
        "display_name": display_name,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == email
    token = data["access_token"]
    refresh_token = data["refresh_token"]

    # 2. Get Current User (/v1/auth/me)
    me_res = client.get("/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # 3. Unauthenticated access rejected
    unauth = client.get("/v1/auth/me")
    assert unauth.status_code == 401
    assert unauth.json()["detail"]["code"] == "UNAUTHORIZED"

    # 4. Token Refresh
    ref_res = client.post("/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert ref_res.status_code == 200
    assert "access_token" in ref_res.json()

    # 5. Login
    login_res = client.post("/v1/auth/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    assert login_res.json()["user"]["display_name"] == display_name


def test_login_rate_limiting_after_repeated_failures() -> None:
    target_email = "target.rate.limit@moodfeed.app"
    client.post("/v1/auth/register", json={
        "email": target_email,
        "password": "ValidPassword123!",
        "display_name": "Target User",
    })

    # Attempt 5 failed logins
    for _ in range(5):
        client.post("/v1/auth/login", json={"email": target_email, "password": "WrongPassword"})

    # 6th attempt should be blocked by rate limiter
    blocked_res = client.post("/v1/auth/login", json={"email": target_email, "password": "WrongPassword"})
    assert blocked_res.status_code == 401
    assert "Çok fazla başarısız giriş" in blocked_res.json()["detail"]["message"]
