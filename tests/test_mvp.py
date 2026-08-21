from fastapi.testclient import TestClient
from backend.main import app
from backend.models import ContentInput, Interaction
from backend.reranking import calculate_spiral_risk, rerank
from backend.scoring import RuleBasedTurkishScorer, ScoreConfig
client = TestClient(app)

def test_health_is_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_scores_are_bounded_and_toxic_content_scores_higher() -> None:
    scorer = RuleBasedTurkishScorer()
    toxic = scorer.analyze(ContentInput(id="toxic", text="Sen aptalsın, defol."))
    neutral = scorer.analyze(ContentInput(id="neutral", text="Toplantı saat üçte başlayacak."))
    assert all(0 <= value <= 1 for value in [toxic.sentiment.score, toxic.toxicity_score, toxic.negativity_score])
    assert toxic.toxicity_score > neutral.toxicity_score

def test_analyze_endpoint_returns_expected_analysis_fields() -> None:
    response = client.post("/analyze", json={"id": "post-001", "text": "Bugün güzel bir gün", "original_score": 0.5})
    body = response.json()
    assert response.status_code == 200
    assert body["content_id"] == "post-001"
    assert body["sentiment"]["label"] == "positive"

def test_rerank_endpoint_returns_risk_and_ranking_data() -> None:
    response = client.post(
        "/rerank",
        json={"contents": [{"id": "first", "text": "berbat ve stresli", "original_score": 0.8}], "interactions": [{"negativity_score": 0.9}], "enabled": True},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["spiral_risk"]["level"] == "high"
    assert body["contents"][0]["reason"]

def test_high_negative_history_increases_spiral_risk() -> None:
    risk = calculate_spiral_risk([Interaction(negativity_score=0.9) for _ in range(5)])
    assert risk.level == "high" and risk.score >= 0.60

def test_empty_history_has_low_zero_spiral_risk() -> None:
    risk = calculate_spiral_risk([])
    assert risk.level == "low" and risk.score == 0.0

def test_disabled_moodfeed_preserves_original_order() -> None:
    contents = [ContentInput(id="first", text="Berbat ve stresli.", original_score=0.9), ContentInput(id="second", text="Güzel ve destekleyici.", original_score=0.1)]
    output, _ = rerank(contents, [], False, RuleBasedTurkishScorer(), ScoreConfig())
    assert [item.content_id for item in output] == ["first", "second"]
    assert [item.new_rank for item in output] == [1, 2]
    assert [item.ranking_score for item in output] == [0.9, 0.1]
    assert "MoodFeed kapalı olduğu için orijinal akış sırası korundu." in output[0].reason

def test_enabled_rerank_returns_reasons_and_transparency() -> None:
    payload = {"contents": [{"id": "a", "text": "Sen aptalsın, defol.", "original_score": 0.9}, {"id": "b", "text": "Umut dolu güzel bir gün.", "original_score": 0.5}], "interactions": [{"negativity_score": 0.9} for _ in range(5)], "enabled": True}
    response = client.post("/rerank", json=payload)
    assert response.status_code == 200 and response.json()["contents"][0]["reason"]
    assert client.get(f"/transparency/{response.json()['contents'][0]['content_id']}").status_code == 200

def test_invalid_request_and_unknown_transparency_return_errors() -> None:
    assert client.post("/analyze", json={"id": "x", "text": ""}).status_code == 422
    assert client.get("/transparency/bilinmeyen").status_code == 404

def test_toggle_changes_feed_mode() -> None:
    toggle_response = client.post("/settings/toggle", json={"enabled": False})
    assert toggle_response.json() == {"enabled": False, "message": "MoodFeed özelliği kapatıldı; orijinal akış sırası korunacaktır."}
    response = client.get("/feed")
    assert response.status_code == 200 and response.json()["moodfeed_enabled"] is False
    client.post("/settings/toggle", json={"enabled": True})

def test_feed_returns_sample_data() -> None:
    response = client.get("/feed")
    assert response.status_code == 200
    assert {item["content_id"] for item in response.json()["contents"]} == {"post-001", "post-002", "post-003", "post-004"}

def test_demo_page_is_available() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "MoodFeed Demo" in response.text

def test_feed_when_disabled_preserves_sample_source_order() -> None:
    client.post("/settings/toggle", json={"enabled": False})
    response = client.get("/feed")
    assert [item["content_id"] for item in response.json()["contents"]] == ["post-001", "post-002", "post-003", "post-004"]
    client.post("/settings/toggle", json={"enabled": True})

def test_rerank_keeps_tied_scores_in_source_order() -> None:
    contents = [ContentInput(id="one", text="nötr", original_score=0.5), ContentInput(id="two", text="nötr", original_score=0.5)]
    output, _ = rerank(contents, [], True, RuleBasedTurkishScorer(), ScoreConfig())
    assert [item.content_id for item in output] == ["one", "two"]
