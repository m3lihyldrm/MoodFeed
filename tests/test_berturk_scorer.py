import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.berturk_scorer import (
    BerturkTurkishScorer,
    normalize_sentiment_label,
    DEFAULT_BERTURK_MODEL,
)
from backend.models import ContentInput
from backend.scoring import RuleBasedTurkishScorer, get_scorer
from backend.main import app


def test_get_scorer_defaults_to_rule_based(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MOODFEED_SCORER", raising=False)
    scorer = get_scorer()
    assert isinstance(scorer, RuleBasedTurkishScorer)


def test_get_scorer_returns_berturk_when_configured(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MOODFEED_SCORER", "berturk")
    scorer = get_scorer()
    assert isinstance(scorer, BerturkTurkishScorer)


def test_label_normalization_handles_standard_and_model_variants() -> None:
    # Positive variants
    assert normalize_sentiment_label("Positive") == "positive"
    assert normalize_sentiment_label("positive") == "positive"
    assert normalize_sentiment_label("olumlu") == "positive"
    assert normalize_sentiment_label("pos") == "positive"
    assert normalize_sentiment_label("LABEL_2") == "positive"
    assert normalize_sentiment_label("2") == "positive"

    # Negative variants
    assert normalize_sentiment_label("Negative") == "negative"
    assert normalize_sentiment_label("negative") == "negative"
    assert normalize_sentiment_label("olumsuz") == "negative"
    assert normalize_sentiment_label("neg") == "negative"
    assert normalize_sentiment_label("LABEL_0") == "negative"
    assert normalize_sentiment_label("0") == "negative"

    # Neutral variants (Omar1010 model uses 'Notr')
    assert normalize_sentiment_label("Notr") == "neutral"
    assert normalize_sentiment_label("nötr") == "neutral"
    assert normalize_sentiment_label("neutral") == "neutral"
    assert normalize_sentiment_label("LABEL_1") == "neutral"
    assert normalize_sentiment_label("1") == "neutral"

    # Invalid raises ValueError
    with pytest.raises(ValueError):
        normalize_sentiment_label("UNKNOWN_LABEL_XYZ")


def test_berturk_scorer_with_mocked_pipeline_produces_valid_analysis() -> None:
    mock_pipeline = MagicMock()
    # Omar1010/bert-turkish-sentiment output format with top_k=None
    mock_pipeline.return_value = [[
        {"label": "Positive", "score": 0.945},
        {"label": "Notr", "score": 0.045},
        {"label": "Negative", "score": 0.010},
    ]]

    scorer = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
    content = ContentInput(id="t-1", text="Bu ürün gerçekten harika ve güzel.")
    result = scorer.analyze(content)

    assert result.content_id == "t-1"
    assert result.sentiment.label == "positive"
    assert result.sentiment.score == 0.945
    assert 0.0 <= result.toxicity_score <= 1.0
    assert 0.0 <= result.negativity_score <= 1.0
    assert any("BERTurk" in r for r in result.reason)
    assert any("klinik" in r for r in result.reason)


def test_berturk_scorer_calculates_toxicity_and_negativity_correctly() -> None:
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [[
        {"label": "Negative", "score": 0.92},
        {"label": "Notr", "score": 0.05},
        {"label": "Positive", "score": 0.03},
    ]]

    scorer = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
    # Text contains toxic word "aptal"
    content = ContentInput(id="t-2", text="Sen ne kadar aptalsın.")
    result = scorer.analyze(content)

    assert result.sentiment.label == "negative"
    assert result.sentiment.score == 0.92
    assert result.toxicity_score > 0.0  # Toxic hit
    # negativity = clamp(0.92 * 0.7 + toxicity_score * 0.3)
    expected_negativity = round(min(1.0, 0.92 * 0.7 + result.toxicity_score * 0.3), 3)
    assert result.negativity_score == expected_negativity


def test_berturk_fallback_when_import_fails() -> None:
    scorer = BerturkTurkishScorer()
    content = ContentInput(id="t-3", text="Bugün hava güzel ve harika.")

    with patch.dict("sys.modules", {"transformers": None}):
        result = scorer.analyze(content)

    assert result.content_id == "t-3"
    assert result.sentiment.label == "positive"
    assert any("[Fallback]" in r for r in result.reason)


def test_berturk_fallback_when_model_load_fails() -> None:
    scorer = BerturkTurkishScorer()
    content = ContentInput(id="t-4", text="Bu yemek berbat ve kötü.")

    with patch("backend.berturk_scorer.BerturkTurkishScorer._load_model", return_value=False):
        scorer._load_error = "Model indirilemedi / bağlantı hatası"
        result = scorer.analyze(content)

    assert result.content_id == "t-4"
    assert result.sentiment.label == "negative"
    assert any("[Fallback]" in r for r in result.reason)


def test_berturk_fallback_when_inference_raises_exception() -> None:
    broken_pipeline = MagicMock(side_effect=RuntimeError("CUDA/OOM memory error"))
    scorer = BerturkTurkishScorer(pipeline_instance=broken_pipeline)
    content = ContentInput(id="t-5", text="Her şey yolunda ve güzel.")

    result = scorer.analyze(content)

    assert result.content_id == "t-5"
    assert result.sentiment.label == "positive"
    assert any("[Fallback]" in r for r in result.reason)


def test_fallback_through_api_returns_200_no_500() -> None:
    client = TestClient(app)
    # Simulate analyze endpoint with a fallback-configured scorer
    fallback_scorer = BerturkTurkishScorer(pipeline_instance=MagicMock(side_effect=Exception("Simulated error")))
    
    with patch("backend.main.scorer", fallback_scorer):
        response = client.post("/analyze", json={"id": "api-1", "text": "Güzel bir haber aldım", "original_score": 0.5})
        assert response.status_code == 200
        body = response.json()
        assert body["content_id"] == "api-1"
        assert body["sentiment"]["label"] == "positive"
        assert any("[Fallback]" in r for r in body["reason"])


def test_bounded_scores_for_all_sentiment_labels() -> None:
    for label, score in [("Positive", 0.999), ("Notr", 0.5), ("Negative", 0.888)]:
        mock_pipeline = MagicMock()
        mock_pipeline.return_value = [[
            {"label": label, "score": score},
            {"label": "Notr" if label != "Notr" else "Positive", "score": 1.0 - score},
        ]]
        scorer = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
        result = scorer.analyze(ContentInput(id="bound-check", text="Test metni"))
        assert 0.0 <= result.sentiment.score <= 1.0
        assert 0.0 <= result.toxicity_score <= 1.0
        assert 0.0 <= result.negativity_score <= 1.0


def test_scorer_info_rule_based() -> None:
    scorer = RuleBasedTurkishScorer()
    info = scorer.get_info()
    assert info.name == "rule_based"
    assert info.label == "Kural Tabanlı"
    assert info.model_name is None
    assert info.fallback is False
    assert info.fallback_reason is None


def test_scorer_info_berturk_active() -> None:
    mock_pipeline = MagicMock()
    scorer = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
    info = scorer.get_info()
    assert info.name == "berturk"
    assert info.label == "BERTurk"
    assert info.model_name == DEFAULT_BERTURK_MODEL
    assert info.fallback is False
    assert info.fallback_reason is None


def test_scorer_info_berturk_fallback_on_load_error() -> None:
    scorer = BerturkTurkishScorer()
    with patch("backend.berturk_scorer.BerturkTurkishScorer._load_model", return_value=False):
        scorer._load_error = "Transformers kütüphanesi eksik"
        info = scorer.get_info()
        assert info.name == "rule_based_fallback"
        assert info.label == "Kural Tabanlı Fallback"
        assert info.fallback is True
        assert info.fallback_reason == "Transformers kütüphanesi eksik"


def test_scorer_info_berturk_fallback_on_inference_error() -> None:
    broken_pipeline = MagicMock(side_effect=RuntimeError("CUDA out of memory"))
    scorer = BerturkTurkishScorer(pipeline_instance=broken_pipeline)
    result = scorer.analyze(ContentInput(id="err-1", text="Test metni"))
    assert result.scorer is not None
    assert result.scorer.name == "rule_based_fallback"
    assert result.scorer.fallback is True
    assert "Inference hatası" in (result.scorer.fallback_reason or "")


def test_api_feed_returns_berturk_scorer_info() -> None:
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [[
        {"label": "Positive", "score": 0.95},
        {"label": "Notr", "score": 0.03},
        {"label": "Negative", "score": 0.02},
    ]]
    mock_scorer = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
    client = TestClient(app)
    with patch("backend.main.scorer", mock_scorer):
        response = client.get("/feed")
        assert response.status_code == 200
        body = response.json()
        assert body["scorer"]["name"] == "berturk"
        assert body["scorer"]["label"] == "BERTurk"
        assert body["scorer"]["fallback"] is False
