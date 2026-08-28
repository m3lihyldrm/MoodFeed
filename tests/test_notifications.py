"""Tests for Real-time User Notifications."""

import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_notifications_lifecycle() -> None:
    uid1 = uuid.uuid4().hex[:8]
    uid2 = uuid.uuid4().hex[:8]

    # User 1 (Author)
    u1_res = client.post("/v1/register", json={
        "email": f"author.{uid1}@moodfeed.app",
        "password": "Password123!",
        "username": f"author_{uid1}",
        "display_name": "Author",
    })
    token1 = u1_res.json()["access_token"]
    u1_id = u1_res.json()["user"]["id"]

    # User 2 (Actor)
    u2_res = client.post("/v1/register", json={
        "email": f"actor.{uid2}@moodfeed.app",
        "password": "Password123!",
        "username": f"actor_{uid2}",
        "display_name": "Actor",
    })
    token2 = u2_res.json()["access_token"]

    # User 1 posts
    p_res = client.post(
        "/v1/posts",
        json={"content": "Bildirim oluşturacak gönderi."},
        headers={"Authorization": f"Bearer {token1}"},
    )
    post_id = p_res.json()["post"]["id"]

    # User 2 likes User 1's post
    client.post(f"/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token2}"})

    # User 2 comments on User 1's post
    client.post(
        f"/v1/posts/{post_id}/comments",
        json={"content": "Harika bir paylaşım!"},
        headers={"Authorization": f"Bearer {token2}"},
    )

    # User 2 follows User 1
    client.post(f"/v1/users/{u1_id}/follow", headers={"Authorization": f"Bearer {token2}"})

    # User 1 checks notifications
    notif_res = client.get("/v1/notifications", headers={"Authorization": f"Bearer {token1}"})
    assert notif_res.status_code == 200
    data = notif_res.json()
    assert data["unread_count"] >= 3
    notifs = data["notifications"]
    types = {n["type"] for n in notifs}
    assert "like" in types
    assert "comment" in types
    assert "follow" in types

    # Mark single notification as read
    first_id = notifs[0]["id"]
    read_res = client.patch(f"/v1/notifications/{first_id}/read", headers={"Authorization": f"Bearer {token1}"})
    assert read_res.status_code == 200

    # Mark all read
    read_all_res = client.patch("/v1/notifications/read-all", headers={"Authorization": f"Bearer {token1}"})
    assert read_all_res.status_code == 200
    assert read_all_res.json()["unread_count"] == 0
