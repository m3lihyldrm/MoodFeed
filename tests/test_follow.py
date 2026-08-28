"""Tests for User Follow/Unfollow and Followers/Following Lists."""

import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_follow_and_unfollow_flow() -> None:
    uid1 = uuid.uuid4().hex[:8]
    uid2 = uuid.uuid4().hex[:8]

    # User 1
    u1_res = client.post("/v1/register", json={
        "email": f"user1.{uid1}@moodfeed.app",
        "password": "Password123!",
        "username": f"user1_{uid1}",
        "display_name": "User One",
    })
    token1 = u1_res.json()["access_token"]
    u1_id = u1_res.json()["user"]["id"]

    # User 2
    u2_res = client.post("/v1/register", json={
        "email": f"user2.{uid2}@moodfeed.app",
        "password": "Password123!",
        "username": f"user2_{uid2}",
        "display_name": "User Two",
    })
    token2 = u2_res.json()["access_token"]
    u2_id = u2_res.json()["user"]["id"]

    # User 1 follows User 2
    follow_res = client.post(f"/v1/users/{u2_id}/follow", headers={"Authorization": f"Bearer {token1}"})
    assert follow_res.status_code == 200
    assert follow_res.json()["is_following"] is True
    assert follow_res.json()["followers_count"] >= 1

    # Check User 2's followers
    f_res = client.get(f"/v1/users/{u2_id}/followers")
    assert f_res.status_code == 200
    followers = f_res.json()["followers"]
    assert any(f["id"] == u1_id for f in followers)

    # Check User 1's following
    ing_res = client.get(f"/v1/users/{u1_id}/following")
    assert ing_res.status_code == 200
    following = ing_res.json()["following"]
    assert any(f["id"] == u2_id for f in following)

    # User 1 unfollows User 2
    unf_res = client.delete(f"/v1/users/{u2_id}/follow", headers={"Authorization": f"Bearer {token1}"})
    assert unf_res.status_code == 200
    assert unf_res.json()["is_following"] is False
