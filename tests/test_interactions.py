"""Tests for User Interactions API and Personalization."""

from __future__ import annotations

from fastapi.testclient import TestClient
from backend.main import app
from backend.models import ContentInput
from backend.reranking import rerank
from backend.scoring import RuleBasedTurkishScorer, ScoreConfig

client = TestClient(app)


def test_post_interaction_like_and_unlike() -> None:
    # 1. Like
    res = client.post(
        "/v1/interactions",
        json={
            "user_id": "test-user-123",
            "content_id": "news-101",
            "action_type": "like",
            "source": "BBC Türkçe",
            "category": "Gündem",
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["success"] is True
    assert data["action"]["action_type"] == "like"
    assert data["action"]["content_id"] == "news-101"

    # 2. Summary reflects liked content
    res_sum = client.get("/v1/interactions/summary?user_id=test-user-123")
    assert res_sum.status_code == 200
    sum_data = res_sum.json()
    assert "news-101" in sum_data["liked_content_ids"]


def test_post_interaction_mute_source_and_summary() -> None:
    # Mute source
    res = client.post(
        "/v1/interactions",
        json={
            "user_id": "test-user-456",
            "content_id": "news-202",
            "action_type": "mute_source",
            "source": "Sputnik Türkiye",
        },
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    # Check summary
    res_sum = client.get("/v1/interactions/summary?user_id=test-user-456")
    assert res_sum.status_code == 200
    assert "Sputnik Türkiye" in res_sum.json()["muted_sources"]


def test_post_interaction_less_like_this() -> None:
    res = client.post(
        "/v1/interactions",
        json={
            "user_id": "test-user-789",
            "content_id": "news-303",
            "action_type": "less_like_this",
            "source": "TRT Haber",
        },
    )
    assert res.status_code == 200
    assert res.json()["success"] is True

    res_sum = client.get("/v1/interactions/summary?user_id=test-user-789")
    assert res_sum.status_code == 200
    assert "news-303" in res_sum.json()["less_like_content_ids"]


def test_get_interactions_history() -> None:
    uid = "11111111-1111-1111-1111-111111111111"
    client.post(
        "/v1/interactions",
        json={
            "user_id": uid,
            "content_id": "news-hist-1",
            "action_type": "like",
            "source": "BBC Türkçe",
        },
    )
    res = client.get(f"/v1/interactions?user_id={uid}")
    assert res.status_code == 200
    items = res.json()
    assert isinstance(items, list)
    assert len(items) >= 1
    assert items[0]["user_id"] == uid
    assert items[0]["content_id"] == "news-hist-1"


def test_rerank_personalization_with_muted_sources_and_less_liked() -> None:
    scorer = RuleBasedTurkishScorer()
    config = ScoreConfig()
    contents = [
        ContentInput(id="item-normal", text="Normal haber metni.", source="TRT Haber", original_score=0.8),
        ContentInput(id="item-muted", text="Sessize alınan kaynak haberi.", source="MutedNews", original_score=0.9),
        ContentInput(id="item-less", text="Daha az benzer istenen haber.", source="DW Türkçe", original_score=0.85),
    ]

    ranked, risk = rerank(
        contents=contents,
        interactions=[],
        enabled=True,
        scorer=scorer,
        config=config,
        muted_sources=["MutedNews"],
        less_liked_ids=["item-less"],
    )

    ranked_by_id = {item.content_id: item for item in ranked}
    
    # Muted source item gets penalized heavily
    assert ranked_by_id["item-muted"].ranking_score < ranked_by_id["item-normal"].ranking_score
    assert any("sessize alındığı için" in r for r in ranked_by_id["item-muted"].reason)

    # Less-liked item gets penalized
    assert any("Daha Az Benzer" in r for r in ranked_by_id["item-less"].reason)
