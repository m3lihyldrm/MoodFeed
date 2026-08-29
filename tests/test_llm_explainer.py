"""Unit and Integration Tests for MoodFeed LLM Complementary Explainer."""

from __future__ import annotations

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.llm_explainer import explain_decision

client = TestClient(app)


def test_explain_decision_high_toxicity() -> None:
    content = {
        "content_id": "post-004",
        "title": "Saldırgan Yorum",
        "text": "Sen ne kadar aptalsın, defol buradan.",
        "author": "TrollHesap",
        "category": "Gündem",
    }
    scores = {
        "toxicity_score": 0.75,
        "negativity_score": 0.90,
        "original_rank": 4,
        "new_rank": 25,
    }
    context = {"profile": "balanced", "scenario": "default"}

    explanation = explain_decision(content, scores, context)
    assert isinstance(explanation, str)
    assert len(explanation) > 30
    assert "toksisite" in explanation.lower() or "saldırganlık" in explanation.lower()
    assert "geriye alındı" in explanation or "geriye çekildi" in explanation or "azaltmak için" in explanation
    assert "Sıralamayı Geri Al" in explanation


def test_explain_decision_high_negativity_and_spiral() -> None:
    content = {
        "content_id": "post-002",
        "title": "Hizmet Şikayeti",
        "text": "Bu hizmet berbat, herkes çok sinirli ve stresli.",
        "author": "Ayşe Kaya",
        "category": "Gündem",
    }
    scores = {
        "toxicity_score": 0.0,
        "negativity_score": 0.85,
        "original_rank": 2,
        "new_rank": 16,
    }
    context = {
        "profile": "calmer",
        "scenario": "high_negativity",
        "spiral_detected": True,
        "recent_interactions_count": 5,
    }

    explanation = explain_decision(content, scores, context)
    assert isinstance(explanation, str)
    assert "negatiflik" in explanation.lower() or "stres" in explanation.lower()
    assert "dengelemek" in explanation.lower() or "maruziyeti" in explanation.lower()
    assert "Sıralamayı Geri Al" in explanation


def test_explain_decision_positive_content() -> None:
    content = {
        "content_id": "post-001",
        "title": "Ekip Çalışması",
        "text": "Bugün ekip arkadaşımın desteğiyle güzel bir ilerleme kaydettik.",
        "author": "Mert Yılmaz",
        "category": "Topluluk",
    }
    scores = {
        "toxicity_score": 0.0,
        "negativity_score": 0.05,
        "original_rank": 5,
        "new_rank": 1,
    }
    context = {"profile": "balanced"}

    explanation = explain_decision(content, scores, context)
    assert isinstance(explanation, str)
    assert "yapıcı" in explanation.lower() or "olumlu" in explanation.lower()
    assert "öne taşındı" in explanation or "çeşitliliğini" in explanation


def test_explain_decision_neutral_content() -> None:
    content = {
        "content_id": "post-013",
        "title": "James Webb Teleskobu",
        "text": "James Webb Teleskobu yeni bir galaksi kümesi tespit etti.",
        "category": "Bilim",
    }
    scores = {
        "toxicity_score": 0.0,
        "negativity_score": 0.02,
        "original_rank": 11,
        "new_rank": 11,
    }
    context = {"profile": "balanced"}

    explanation = explain_decision(content, scores, context)
    assert isinstance(explanation, str)
    assert "bilgilendirici" in explanation.lower() or "dengeli" in explanation.lower()
    assert "korundu" in explanation


def test_explain_decision_handles_empty_or_none() -> None:
    explanation = explain_decision(None, None, None)
    assert isinstance(explanation, str)
    assert len(explanation) > 20
    assert "Sıralamayı Geri Al" in explanation


def test_explain_decision_sentence_structure() -> None:
    content = {"text": "Örnek metin", "category": "Teknoloji"}
    scores = {"toxicity_score": 0.6, "negativity_score": 0.8, "original_rank": 1, "new_rank": 10}
    context = {"scenario": "high_negativity"}

    explanation = explain_decision(content, scores, context)
    sentences = [s.strip() for s in explanation.split(".") if s.strip()]
    assert 2 <= len(sentences) <= 4


def test_api_v1_explain_endpoint() -> None:
    payload = {
        "content": {
            "content_id": "post-002",
            "title": "Hizmet Şikayeti",
            "text": "Bu hizmet berbat, herkes çok sinirli ve stresli.",
            "author": "Ayşe Kaya",
            "category": "Gündem",
        },
        "scores": {
            "toxicity_score": 0.0,
            "negativity_score": 0.85,
            "original_rank": 2,
            "new_rank": 16,
        },
        "context": {
            "profile": "balanced",
            "scenario": "high_negativity",
            "spiral_detected": True,
        },
    }

    res = client.post("/v1/explain", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "explanation" in data
    assert len(data["explanation"]) > 20
    assert data["source"] == "llm_explainer"
    assert data["confidence"] >= 0.9


def test_demo_page_contains_ai_explanation() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "AI Açıklaması" in html
    assert "drawer-ai-explanation" in html
    assert "LLM Tamamlayıcı" in html or "LLM Yorumlayıcı" in html or "Kural Tabanlı Açıklama" in html
