"""Tests for Post Like/Unlike endpoints."""

import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_like_and_unlike_post() -> None:
    uid = uuid.uuid4().hex[:8]
    # Register user
    reg = client.post("/v1/register", json={
        "email": f"like.tester.{uid}@moodfeed.app",
        "password": "Password123!",
        "username": f"liker_{uid}",
        "display_name": "Liker User",
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]

    # Create post
    post_res = client.post(
        "/v1/posts",
        json={"content": "Beğeni testi için harika bir gönderi!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert post_res.status_code == 200
    post_id = post_res.json()["post"]["id"]

    # Like (Toggle ON)
    like_res = client.post(f"/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    assert like_res.status_code == 200
    data = like_res.json()
    assert data["liked"] is True
    assert data["likes_count"] >= 1

    # Like (Toggle OFF)
    unlike_res = client.post(f"/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    assert unlike_res.status_code == 200
    data2 = unlike_res.json()
    assert data2["liked"] is False

    # Explicit DELETE unlike
    client.post(f"/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    del_res = client.delete(f"/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200
    assert del_res.json()["liked"] is False
