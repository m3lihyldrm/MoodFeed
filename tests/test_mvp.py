from fastapi.testclient import TestClient
from backend.main import app
from backend.models import ContentInput, Interaction
from backend.reranking import calculate_spiral_risk, rerank
from backend.scoring import RuleBasedTurkishScorer, ScoreConfig
client = TestClient(app)

def test_health_is_ok() -> None:
    assert client.get("/health").json() == {"status": "ok"}

def test_scores_are_bounded_and_toxic_content_scores_higher() -> None:
    scorer = RuleBasedTurkishScorer()
    toxic = scorer.analyze(ContentInput(id="toxic", text="Sen aptalsın, defol."))
    neutral = scorer.analyze(ContentInput(id="neutral", text="Toplantı saat üçte başlayacak."))
    assert all(0 <= value <= 1 for value in [toxic.sentiment.score, toxic.toxicity_score, toxic.negativity_score])
    assert toxic.toxicity_score > neutral.toxicity_score

def test_high_negative_history_increases_spiral_risk() -> None:
    risk = calculate_spiral_risk([Interaction(negativity_score=0.9) for _ in range(5)])
    assert risk.level == "high" and risk.score >= 0.60

def test_disabled_moodfeed_preserves_original_order() -> None:
    contents = [ContentInput(id="first", text="Berbat ve stresli.", original_score=0.9), ContentInput(id="second", text="Güzel ve destekleyici.", original_score=0.1)]
    output, _ = rerank(contents, [], False, RuleBasedTurkishScorer(), ScoreConfig())
    assert [item.content_id for item in output] == ["first", "second"]
    assert [item.new_rank for item in output] == [1, 2]

def test_enabled_rerank_returns_reasons_and_transparency() -> None:
    payload = {"contents": [{"id": "a", "text": "Sen aptalsın, defol.", "original_score": 0.9}, {"id": "b", "text": "Umut dolu güzel bir gün.", "original_score": 0.5}], "interactions": [{"negativity_score": 0.9} for _ in range(5)], "enabled": True}
    response = client.post("/rerank", json=payload)
    assert response.status_code == 200 and response.json()["contents"][0]["reason"]
    assert client.get(f"/transparency/{response.json()['contents'][0]['content_id']}").status_code == 200

def test_invalid_request_and_unknown_transparency_return_errors() -> None:
    assert client.post("/analyze", json={"id": "x", "text": ""}).status_code == 422
    assert client.get("/transparency/bilinmeyen").status_code == 404

def test_toggle_changes_feed_mode() -> None:
    assert client.post("/settings/toggle", json={"enabled": False}).json()["enabled"] is False
    response = client.get("/feed")
    assert response.status_code == 200 and response.json()["moodfeed_enabled"] is False
    client.post("/settings/toggle", json={"enabled": True})
