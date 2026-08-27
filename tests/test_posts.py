"""Tests for MoodFeed Posts, Likes, Saves, and User Profile."""

import uuid
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_post_creation_and_listing() -> None:
    uid = uuid.uuid4().hex[:8]
    # 1. Register a creator user
    user_res = client.post("/v1/register", json={
        "email": f"post.creator.{uid}@moodfeed.app",
        "password": "GuvenliSifre123!",
        "username": f"post_creator_{uid}",
        "display_name": "Post Creator",
    })
    assert user_res.status_code == 200
    token = user_res.json()["access_token"]
    user_id = user_res.json()["user"]["id"]

    # 2. Create a positive post
    create_res = client.post(
        "/v1/posts",
        json={"content": "Harika bir gün! Açık kaynak projelerine katkıda bulunmak çok mutluluk verici #teknoloji"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert create_res.status_code == 200
    post_data = create_res.json()["post"]
    post_id = post_data["id"]
    assert post_data["sentiment"]["label"] == "positive"
    assert post_data["toxicity_score"] <= 0.2

    # 3. Get Post Detail
    detail_res = client.get(f"/v1/posts/{post_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == post_id

    # 4. Like Post (Toggle on / off)
    like_res1 = client.post(f"/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    assert like_res1.status_code == 200
    assert like_res1.json()["liked"] is True
    assert like_res1.json()["likes_count"] == 1

    like_res2 = client.post(f"/v1/posts/{post_id}/like", headers={"Authorization": f"Bearer {token}"})
    assert like_res2.status_code == 200
    assert like_res2.json()["liked"] is False
    assert like_res2.json()["likes_count"] == 0

    # 5. Save Post (Toggle on / off)
    save_res1 = client.post(f"/v1/posts/{post_id}/save", headers={"Authorization": f"Bearer {token}"})
    assert save_res1.status_code == 200
    assert save_res1.json()["saved"] is True

    # 6. Check User Profile Endpoint
    profile_res = client.get(f"/v1/users/{user_id}/profile")
    assert profile_res.status_code == 200
    prof_data = profile_res.json()
    assert prof_data["user"]["username"] == f"post_creator_{uid}"
    assert prof_data["posts_count"] >= 1
    assert prof_data["saves_count"] >= 1
