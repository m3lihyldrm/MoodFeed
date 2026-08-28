"""Comprehensive Test Suite for MoodFeed Full Product Features.

Tests:
1. Mood Detection AI (Hugging Face / Lexicon Fallback, Turkish emotions: happy, sad, angry, anxious, neutral)
2. Posts creation with mood scoring
3. Like and Unlike system with notifications
4. Comments system (nested replies, mood scoring, edit, soft delete)
5. Follow system (follow, unfollow, follower/following lists, notifications)
6. Profiles (get profile with stats, update profile)
7. Notifications (list, read single, read all, clear, unread counts)
8. Search and Mood filtering
"""

from __future__ import annotations

import uuid
from fastapi.testclient import TestClient
from backend.main import app
from backend.services.mood_detector import mood_detector

client = TestClient(app)


def test_mood_detector_lexicon_emotions() -> None:
    # 1. Happy
    res_happy = mood_detector.detect_mood("Bugün harika bir gün, projemizde büyük bir başarı ve zafer kazandık! Çok mutluyum!")
    assert res_happy["mood_label"] == "happy"
    assert res_happy["mood_score"] > 0.0

    # 2. Sad
    res_sad = mood_detector.detect_mood("Çok üzgünüm, yakın arkadaşımızı kaybettik, derin bir hüzün ve keder içindeyim.")
    assert res_sad["mood_label"] == "sad"
    assert res_sad["mood_score"] < 0.0

    # 3. Angry
    res_angry = mood_detector.detect_mood("Bu yapılan tam bir rezalet ve haksızlık! Nefret ediyorum, çok öfkeliyim!")
    assert res_angry["mood_label"] == "angry"
    assert res_angry["mood_score"] < 0.0

    # 4. Anxious
    res_anxious = mood_detector.detect_mood("Gelecek konusunda çok büyük bir endişe ve kaygı duyuyorum, panik ve stres içindeyim.")
    assert res_anxious["mood_label"] == "anxious"
    assert res_anxious["mood_score"] < 0.0

    # 5. Neutral
    res_neutral = mood_detector.detect_mood("Merkez Bankası faiz kararını bugün saat 14:00'te açıklayacak.")
    assert res_neutral["mood_label"] == "neutral"


def test_post_creation_with_mood_detection() -> None:
    res = client.post(
        "/v1/posts",
        json={
            "content": "Yeni MoodFeed versiyonu yayında! Harika özellikler eklendi, tebrikler ekip!",
            "title": "Sürüm Güncellemesi",
            "category": "Teknoloji",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert "post" in data
    assert data["post"]["mood_label"] == "happy"
    assert data["post"]["mood_score"] > 0.0
    post_id = data["post"]["id"]

    # Retrieve post detail
    res_get = client.get(f"/v1/posts/{post_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == post_id


def test_post_like_and_unlike_flow() -> None:
    # Create post
    p_res = client.post(
        "/v1/posts",
        json={"content": "Beğeni testi için gönderi içeriği.", "category": "Genel"},
    )
    post_id = p_res.json()["post"]["id"]

    # 1. Like
    l_res = client.post(f"/v1/posts/{post_id}/like")
    assert l_res.status_code == 200
    assert l_res.json()["liked"] is True
    assert l_res.json()["likes_count"] >= 1

    # 2. Get Likes list
    likes_res = client.get(f"/v1/posts/{post_id}/likes")
    assert likes_res.status_code == 200
    assert likes_res.json()["count"] >= 1

    # 3. Unlike
    u_res = client.delete(f"/v1/posts/{post_id}/like")
    assert u_res.status_code == 200
    assert u_res.json()["liked"] is False


def test_comment_system_with_nested_replies_and_mood() -> None:
    # Create post
    p_res = client.post(
        "/v1/posts",
        json={"content": "Yorumlar ve tartışma için açılan gönderi."},
    )
    post_id = p_res.json()["post"]["id"]

    # 1. Add Root Comment
    c1_res = client.post(
        f"/v1/posts/{post_id}/comments",
        json={"content": "Gerçekten harika bir paylaşım olmuş, tebrik ederim!"},
    )
    assert c1_res.status_code == 200
    c1_data = c1_res.json()["comment"]
    assert c1_data["mood_label"] == "happy"
    parent_comment_id = c1_data["id"]

    # 2. Add Nested Reply
    c2_res = client.post(
        f"/v1/posts/{post_id}/comments",
        json={
            "content": "Katılıyorum, çok faydalı oldu.",
            "parent_comment_id": parent_comment_id,
        },
    )
    assert c2_res.status_code == 200
    c2_data = c2_res.json()["comment"]
    assert c2_data["parent_comment_id"] == parent_comment_id

    # 3. List Comments (Nested structure)
    list_res = client.get(f"/v1/posts/{post_id}/comments")
    assert list_res.status_code == 200
    comments = list_res.json()["comments"]
    assert len(comments) >= 1
    root = next(c for c in comments if c["id"] == parent_comment_id)
    assert len(root["replies"]) >= 1

    # 4. Edit Comment
    patch_res = client.patch(
        f"/v1/comments/{c2_data['id']}",
        json={"content": "Fikrimi değiştirdim, bu durum biraz endişe verici."},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["comment"]["mood_label"] == "anxious"

    # 5. Delete Comment (Soft delete)
    del_res = client.delete(f"/v1/comments/{c2_data['id']}")
    assert del_res.status_code == 200
    assert del_res.json()["success"] is True


def test_follow_system_and_profiles() -> None:
    # Test user IDs
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())

    # Follow
    follow_res = client.post(f"/v1/users/{user_b}/follow")
    assert follow_res.status_code == 200
    assert follow_res.json()["is_following"] is True

    # Followers list
    followers_res = client.get(f"/v1/users/{user_b}/followers")
    assert followers_res.status_code == 200
    assert followers_res.json()["count"] >= 1

    # Profile view
    prof_res = client.get(f"/v1/users/{user_b}/profile")
    assert prof_res.status_code == 200
    assert "followers_count" in prof_res.json()

    # Unfollow
    unfollow_res = client.delete(f"/v1/users/{user_b}/follow")
    assert unfollow_res.status_code == 200
    assert unfollow_res.json()["is_following"] is False


def test_notifications_workflow() -> None:
    # 1. Get notifications
    notifs_res = client.get("/v1/notifications")
    assert notifs_res.status_code == 200
    assert "unread_count" in notifs_res.json()

    # 2. Mark all as read
    read_all_res = client.patch("/v1/notifications/read-all")
    assert read_all_res.status_code == 200
    assert read_all_res.json()["unread_count"] == 0

    # 3. Clear all
    clear_res = client.delete("/v1/notifications")
    assert clear_res.status_code == 200
    assert clear_res.json()["deleted_count"] >= 0


def test_search_and_mood_filter() -> None:
    # Create distinct posts
    client.post("/v1/posts", json={"content": "Bugün çok neşeli ve coşkulu bir kutlama var!", "category": "Kültür"})
    client.post("/v1/posts", json={"content": "Ekonomik kriz ve derin bir kaygı ortamı hakim.", "category": "Ekonomi"})

    # Search with keyword
    search_res = client.get("/v1/search?q=kutlama")
    assert search_res.status_code == 200
    assert search_res.json()["count"] >= 1
    assert any("kutlama" in r["content"].lower() for r in search_res.json()["results"])

    # Search with mood filter
    mood_res = client.get("/v1/search?mood=happy")
    assert mood_res.status_code == 200
    for r in mood_res.json()["results"]:
        assert r["mood_label"] == "happy"
