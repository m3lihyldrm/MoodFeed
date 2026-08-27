"""Tests for MoodFeed Persistent Authentication and User Registration."""

import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_user_registration_success() -> None:
    uid = uuid.uuid4().hex[:8]
    email = f"user.{uid}@moodfeed.app"
    password = "GuvenliSifre123!"
    username = f"user_{uid}"
    display_name = "Yeni Kullanıcı"

    res = client.post("/v1/register", json={
        "email": email,
        "password": password,
        "username": username,
        "display_name": display_name,
    })
    assert res.status_code == 200
    data = res.json()
    assert data["user"]["email"] == email
    assert data["user"]["username"] == username
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_duplicate_registration_fails() -> None:
    uid = uuid.uuid4().hex[:8]
    email = f"duplicate.{uid}@moodfeed.app"
    password = "GuvenliSifre123!"

    res1 = client.post("/v1/register", json={
        "email": email,
        "password": password,
        "username": f"dup_{uid}_1",
    })
    assert res1.status_code == 200

    # Duplicate email
    res2 = client.post("/v1/register", json={
        "email": email,
        "password": password,
        "username": f"dup_{uid}_2",
    })
    assert res2.status_code == 400
    assert "Bu e-posta adresiyle kayıtlı bir hesap zaten var" in res2.json()["detail"]["message"]


def test_user_login_success_and_failure() -> None:
    uid = uuid.uuid4().hex[:8]
    email = f"login.{uid}@moodfeed.app"
    password = "DogruSifre123!"

    client.post("/v1/register", json={
        "email": email,
        "password": password,
        "username": f"login_user_{uid}",
    })

    # Successful login
    login_res = client.post("/v1/login", json={"email": email, "password": password})
    assert login_res.status_code == 200
    login_data = login_res.json()
    assert "access_token" in login_data
    token = login_data["access_token"]

    # Verify /v1/me with token
    me_res = client.get("/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert me_res.status_code == 200
    assert me_res.json()["email"] == email

    # Failed login with wrong password
    fail_res = client.post("/v1/login", json={"email": email, "password": "YanlisSifre"})
    assert fail_res.status_code == 401


def test_user_logout() -> None:
    res = client.post("/v1/logout")
    assert res.status_code == 200
    assert res.json()["success"] is True
