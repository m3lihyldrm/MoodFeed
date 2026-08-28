"""Tests for Search and Mood Filtering endpoints."""

import uuid
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_search_and_mood_filters() -> None:
    uid = uuid.uuid4().hex[:8]
    # Register user
    reg = client.post("/v1/register", json={
        "email": f"search.tester.{uid}@moodfeed.app",
        "password": "Password123!",
        "username": f"searcher_{uid}",
        "display_name": "Searcher",
    })
    token = reg.json()["access_token"]

    # 1. Create a happy post
    client.post(
        "/v1/posts",
        json={"content": "Yapay zeka teknolojisi çok heyecan verici ve mutlu etti #teknoloji"},
        headers={"Authorization": f"Bearer {token}"},
    )

    # 2. Search by query
    s1 = client.get("/v1/search?q=teknoloji")
    assert s1.status_code == 200
    res1 = s1.json()
    assert res1["count"] >= 1
    assert any("teknoloji" in p["content"].lower() for p in res1["posts"])

    # 3. Filter by mood
    s2 = client.get("/v1/search?mood=happy")
    assert s2.status_code == 200
    res2 = s2.json()
    assert all(p["mood_label"] == "happy" for p in res2["posts"])

    # 4. Non-matching query returns empty result
    s3 = client.get("/v1/search?q=kesinlikleboylebirseyyokxyz12345")
    assert s3.status_code == 200
    assert s3.json()["count"] == 0
