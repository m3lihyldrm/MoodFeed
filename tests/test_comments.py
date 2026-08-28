"""Tests for Post Comments and Nested Replies."""

import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_create_and_nest_comments() -> None:
    uid = uuid.uuid4().hex[:8]
    # Register user
    reg = client.post("/v1/register", json={
        "email": f"comment.tester.{uid}@moodfeed.app",
        "password": "Password123!",
        "username": f"commenter_{uid}",
        "display_name": "Commenter User",
    })
    assert reg.status_code == 200
    token = reg.json()["access_token"]

    # Create post
    post_res = client.post(
        "/v1/posts",
        json={"content": "Yorum testi için açılan başlık"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert post_res.status_code == 200
    post_id = post_res.json()["post"]["id"]

    # 1. Root Comment (Happy)
    c1_res = client.post(
        f"/v1/posts/{post_id}/comments",
        json={"content": "Bu haber gerçekten çok mutlu etti ve sevindirdi!"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert c1_res.status_code == 200
    c1_data = c1_res.json()["comment"]
    assert c1_data["mood_label"] == "happy"
    assert c1_data["mood_score"] > 0.0
    c1_id = c1_data["id"]

    # 2. Nested Reply
    reply_res = client.post(
        f"/v1/posts/{post_id}/comments",
        json={"content": "Ben de tamamen katılıyorum, tebrikler!", "parent_comment_id": c1_id},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert reply_res.status_code == 200
    reply_data = reply_res.json()["comment"]
    assert reply_data["parent_comment_id"] == c1_id

    # 3. List Comments
    list_res = client.get(f"/v1/posts/{post_id}/comments")
    assert list_res.status_code == 200
    comments = list_res.json()["comments"]
    assert len(comments) >= 1
    assert len(comments[0]["replies"]) >= 1

    # 4. Soft Delete Comment
    del_res = client.delete(f"/v1/comments/{c1_id}", headers={"Authorization": f"Bearer {token}"})
    assert del_res.status_code == 200
