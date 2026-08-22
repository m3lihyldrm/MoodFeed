"""Production User Persistence & State Tests."""

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def get_authenticated_headers() -> dict[str, str]:
    email = "persist.user@moodfeed.app"
    password = "PersistPassword123!"
    reg = client.post("/v1/auth/register", json={
        "email": email,
        "password": password,
        "display_name": "Persist User",
    })
    token = reg.json().get("access_token")
    if not token:
        login = client.post("/v1/auth/login", json={"email": email, "password": password})
        token = login.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_user_preferences_persistence_and_patch() -> None:
    headers = get_authenticated_headers()

    # 1. Get initial preferences
    res = client.get("/v1/preferences", headers=headers)
    assert res.status_code == 200
    assert res.json()["profile_preset"] == "balanced"

    # 2. Patch preference
    patch_res = client.patch("/v1/preferences", json={"profile_preset": "calmer", "low_intensity_mode": True}, headers=headers)
    assert patch_res.status_code == 200
    assert patch_res.json()["profile_preset"] == "calmer"
    assert patch_res.json()["low_intensity_mode"] is True

    # 3. Verify persistence
    verify = client.get("/v1/preferences", headers=headers)
    assert verify.json()["profile_preset"] == "calmer"

    # 4. Reset preferences
    reset_res = client.post("/v1/preferences/reset", headers=headers)
    assert reset_res.status_code == 200
    assert reset_res.json()["profile_preset"] == "balanced"


def test_saved_items_and_mute_rules_persistence() -> None:
    headers = get_authenticated_headers()

    # 1. Save item
    save_res = client.post("/v1/saved", json={"content_id": "post-001"}, headers=headers)
    assert save_res.status_code == 200
    assert save_res.json()["saved"] is True

    # 2. List saved items
    list_saved = client.get("/v1/saved", headers=headers)
    assert "post-001" in list_saved.json()["saved_ids"]

    # 3. Remove saved item
    del_res = client.delete("/v1/saved/post-001", headers=headers)
    assert del_res.status_code == 200
    assert del_res.json()["removed"] is True

    # 4. Mute source
    mute_res = client.post("/v1/muted/source", json={"source_name": "Rahatsız Edici Kaynak"}, headers=headers)
    assert mute_res.status_code == 200

    # 5. List muted
    muted_list = client.get("/v1/muted", headers=headers)
    assert "Rahatsız Edici Kaynak" in muted_list.json()["muted_sources"]

    # 6. Unmute source
    unmute_res = client.delete("/v1/muted/source/Rahatsız Edici Kaynak", headers=headers)
    assert unmute_res.status_code == 200


def test_feedback_and_data_export_persistence() -> None:
    headers = get_authenticated_headers()

    # 1. Submit feedback
    fb_res = client.post("/v1/feedback", json={
        "content_id": "post-002",
        "action": "less_like_this",
        "note": "Bu tür yoğun şikayet içeriklerini daha az görmek istiyorum.",
    }, headers=headers)
    assert fb_res.status_code == 200
    assert fb_res.json()["feedback_action"] == "less_like_this"

    # 2. Get feedback history
    fb_hist = client.get("/v1/feedback/history", headers=headers)
    assert fb_hist.status_code == 200
    assert len(fb_hist.json()["feedbacks"]) >= 1

    # 3. Request data export (Portability)
    exp_res = client.post("/v1/privacy/data/export", json={"format": "json"}, headers=headers)
    assert exp_res.status_code == 200
    assert exp_res.json()["status"] == "ready"
    assert "preferences" in exp_res.json()["data"]
