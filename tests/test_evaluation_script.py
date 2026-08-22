import csv
import json
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from backend.berturk_scorer import BerturkTurkishScorer
from backend.models import ContentInput, ScorerInfo
from backend.scoring import RuleBasedTurkishScorer
from scripts.evaluate_scorers import (
    ORDERED_LABELS,
    calculate_metrics,
    evaluate_berturk,
    evaluate_rule_based,
    load_dataset,
    run_evaluation,
    validate_dataset,
    write_errors,
    write_metrics,
)

DATASET_PATH = Path("data/evaluation_sentiment.csv")


def test_dataset_exists_and_has_valid_headers() -> None:
    assert DATASET_PATH.is_file(), f"Veri seti bulunamadı: {DATASET_PATH}"
    data = load_dataset(DATASET_PATH)
    assert len(data) == 90, f"Beklenen 90 satır veri, bulunan: {len(data)}"
    for item in data:
        assert "text" in item and item["text"]
        assert "label" in item and item["label"] in {"positive", "neutral", "negative"}


def test_dataset_class_distribution_is_balanced_30_each() -> None:
    data = load_dataset(DATASET_PATH)
    counts = validate_dataset(data)
    assert counts["positive"] == 30, f"Pozitif sayısı 30 olmalı, bulunan: {counts['positive']}"
    assert counts["neutral"] == 30, f"Nötr sayısı 30 olmalı, bulunan: {counts['neutral']}"
    assert counts["negative"] == 30, f"Negatif sayısı 30 olmalı, bulunan: {counts['negative']}"


def test_dataset_contains_no_conflicting_duplicates() -> None:
    data = load_dataset(DATASET_PATH)
    seen_texts: dict[str, str] = {}
    for item in data:
        txt = item["text"].strip().lower()
        lbl = item["label"]
        if txt in seen_texts:
            assert seen_texts[txt] == lbl, f"Aynı metin farklı etiketlerle bulundu: {txt}"
        seen_texts[txt] = lbl


def test_calculate_metrics_with_handcrafted_sample() -> None:
    # 6 örnek: 2 neg, 2 neu, 2 pos
    y_true = ["negative", "negative", "neutral", "neutral", "positive", "positive"]
    y_pred = ["negative", "neutral",  "neutral", "positive", "positive", "positive"]

    metrics = calculate_metrics(y_true, y_pred)

    # Doğru tahminler: neg->neg (1), neu->neu (1), pos->pos (2) => 4/6 = 0.6667
    assert metrics["accuracy"] == 0.6667
    assert "confusion_matrix" in metrics
    cm = metrics["confusion_matrix"]
    # cm satırları: negative, neutral, positive
    # Negative satırı (2 gerçek neg): [1 pred neg, 1 pred neu, 0 pred pos]
    assert cm[0] == [1, 1, 0]
    # Neutral satırı (2 gerçek neu): [0 pred neg, 1 pred neu, 1 pred pos]
    assert cm[1] == [0, 1, 1]
    # Positive satırı (2 gerçek pos): [0 pred neg, 0 pred neu, 2 pred pos]
    assert cm[2] == [0, 0, 2]

    # Negative: TP=1, FP=0, FN=1 -> Prec=1.0, Rec=0.5, F1=0.6667
    # Neutral:  TP=1, FP=1, FN=1 -> Prec=0.5, Rec=0.5, F1=0.5000
    # Positive: TP=2, FP=1, FN=0 -> Prec=0.6667, Rec=1.0, F1=0.8000
    assert metrics["class_metrics"]["negative"]["precision"] == 1.0
    assert metrics["class_metrics"]["negative"]["recall"] == 0.5
    assert metrics["class_metrics"]["neutral"]["precision"] == 0.5
    assert metrics["class_metrics"]["neutral"]["recall"] == 0.5
    assert metrics["class_metrics"]["positive"]["recall"] == 1.0

    # Macro ortalamalar
    assert metrics["macro_precision"] == 0.7222
    assert metrics["macro_recall"] == 0.6667
    assert metrics["macro_f1"] == 0.6556


def test_calculate_metrics_confusion_matrix_order() -> None:
    assert ORDERED_LABELS == ["negative", "neutral", "positive"]
    metrics = calculate_metrics(["positive"], ["positive"])
    cm = metrics["confusion_matrix"]
    assert len(cm) == 3
    assert all(len(row) == 3 for row in cm)
    # 1 adet positive -> cm[2][2] == 1, diğerleri 0
    assert cm[2][2] == 1
    assert cm[0][0] == 0 and cm[1][1] == 0


def test_evaluate_rule_based_executes_and_returns_valid_structure() -> None:
    data = load_dataset(DATASET_PATH)
    metrics, errors = evaluate_rule_based(data)

    assert 0.0 <= metrics["accuracy"] <= 1.0
    assert 0.0 <= metrics["macro_precision"] <= 1.0
    assert 0.0 <= metrics["macro_recall"] <= 1.0
    assert 0.0 <= metrics["macro_f1"] <= 1.0
    assert len(metrics["confusion_matrix"]) == 3

    # Hatalar listesinde doğru anahtarlar olmalı
    for err in errors:
        assert err["scorer"] == "rule_based"
        assert "content_id" in err
        assert "text" in err
        assert "true_label" in err
        assert "predicted_label" in err
        assert err["true_label"] != err["predicted_label"]


def test_evaluate_berturk_returns_null_metrics_when_model_load_fails() -> None:
    data = [
        {"text": "Harika bir gün.", "label": "positive"},
        {"text": "Kötü bir haber aldık.", "label": "negative"},
    ]
    mock_scorer = MagicMock(spec=BerturkTurkishScorer)
    mock_scorer._is_loaded = False
    mock_scorer._load_error = "PyTorch bulunamadı."
    mock_scorer.get_info.return_value = ScorerInfo(
        name="rule_based_fallback",
        label="Kural Tabanlı Fallback",
        model_name="Omar1010/bert-turkish-sentiment",
        fallback=True,
        fallback_reason="PyTorch bulunamadı.",
    )

    metrics, errors, reason = evaluate_berturk(data, scorer=mock_scorer)

    # Model yüklenemediğinde metrik null (None) olmalı, sahte metrik üretilmemeli
    assert metrics is None
    assert errors == []
    assert reason is not None
    assert "PyTorch" in reason or "kullanılamıyor" in reason


def test_evaluate_berturk_with_mocked_loaded_pipeline() -> None:
    mock_pipeline = MagicMock()
    # Mock inference responses for 3 samples
    mock_pipeline.side_effect = [
        [[{"label": "Positive", "score": 0.95}, {"label": "Notr", "score": 0.03}, {"label": "Negative", "score": 0.02}]],
        [[{"label": "Notr", "score": 0.90}, {"label": "Positive", "score": 0.05}, {"label": "Negative", "score": 0.05}]],
        [[{"label": "Negative", "score": 0.92}, {"label": "Notr", "score": 0.05}, {"label": "Positive", "score": 0.03}]],
    ]

    scorer = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
    test_data = [
        {"text": "Güzel ve harika bir gün.", "label": "positive"},
        {"text": "Saat 14.00'te toplantı var.", "label": "neutral"},
        {"text": "Bu sistem çok kötü.", "label": "negative"},
    ]

    metrics, errors, reason = evaluate_berturk(test_data, scorer=scorer)

    assert metrics is not None
    assert reason is None
    assert metrics["accuracy"] == 1.0
    assert metrics["macro_f1"] == 1.0
    assert len(errors) == 0


def test_write_metrics_and_write_errors(tmp_path: Path) -> None:
    metrics_file = tmp_path / "artifacts" / "evaluation_metrics.json"
    errors_file = tmp_path / "artifacts" / "evaluation_errors.csv"

    sample_metrics = {
        "evaluation_timestamp": "2026-08-21T17:00:00Z",
        "dataset_type": "synthetic",
        "dataset_warning": "Sentetik test seti uyarısı",
        "sample_count": 2,
        "class_distribution": {"negative": 1, "neutral": 0, "positive": 1},
        "metrics": {
            "rule_based": {"accuracy": 0.5, "macro_f1": 0.5, "confusion_matrix": [[0]]},
            "berturk": None,
        },
        "errors_file": str(errors_file),
        "berturk_status": {"loaded": False, "reason": "Test ortamı"},
    }

    sample_errors = [
        {
            "content_id": "eval-rule-001",
            "text": "Örnek metin",
            "true_label": "positive",
            "predicted_label": "neutral",
            "scorer": "rule_based",
        }
    ]

    write_metrics(metrics_file, sample_metrics)
    write_errors(errors_file, sample_errors)

    assert metrics_file.is_file()
    assert errors_file.is_file()

    with open(metrics_file, "r", encoding="utf-8") as f:
        loaded_json = json.load(f)
    assert loaded_json["sample_count"] == 2
    assert loaded_json["metrics"]["berturk"] is None

    with open(errors_file, "r", encoding="utf-8") as f:
        reader = list(csv.DictReader(f))
    assert len(reader) == 1
    assert reader[0]["true_label"] == "positive"
    assert reader[0]["predicted_label"] == "neutral"


def test_run_evaluation_orchestration_creates_artifacts_safely(tmp_path: Path) -> None:
    artifacts_dir = tmp_path / "artifacts"
    result = run_evaluation(
        dataset_path=DATASET_PATH,
        artifacts_dir=artifacts_dir,
        include_berturk=False,
    )

    assert result["dataset_type"] == "synthetic"
    assert result["sample_count"] == 90
    assert result["metrics"]["rule_based"] is not None
    assert result["metrics"]["berturk"] is None
    assert (artifacts_dir / "evaluation_metrics.json").is_file()
    assert (artifacts_dir / "evaluation_errors.csv").is_file()


def test_scorer_metadata_and_reasons_contain_mode_and_tags() -> None:
    rule_scorer = RuleBasedTurkishScorer()
    res_rule = rule_scorer.analyze(ContentInput(id="r-1", text="Bugün çok güzel ve harika."))
    assert res_rule.scorer is not None
    assert res_rule.scorer.mode == "rule_based"
    assert res_rule.scorer.is_experimental is False
    assert any("[Kural Tabanlı Skorlama]" in r for r in res_rule.reason)

    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [[
        {"label": "Positive", "score": 0.95},
        {"label": "Notr", "score": 0.03},
        {"label": "Negative", "score": 0.02},
    ]]
    bert_scorer = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
    res_bert = bert_scorer.analyze(ContentInput(id="b-1", text="Bugün çok güzel ve harika."))
    assert res_bert.scorer is not None
    assert res_bert.scorer.mode == "berturk"
    assert res_bert.scorer.is_experimental is True
    assert any("[Deneysel BERTurk]" in r for r in res_bert.reason)
