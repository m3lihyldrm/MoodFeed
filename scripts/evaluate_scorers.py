"""MoodFeed Scorer Değerlendirme Scripti.

Bu script, kural tabanlı duygu analizi (RuleBasedTurkishScorer) ile hazır fine-tuned
BERTurk modelini (BerturkTurkishScorer) aynı sentetik test veri seti üzerinde
karşılaştırarak değerlendirir.
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
import logging
from pathlib import Path
import sys
from typing import Any

# Proje kök dizinini sys.path'e ekle
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.berturk_scorer import BerturkTurkishScorer
from backend.models import ContentInput
from backend.scoring import RuleBasedTurkishScorer

logger = logging.getLogger("moodfeed.evaluation")
logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

ORDERED_LABELS = ["negative", "neutral", "positive"]
VALID_LABELS = set(ORDERED_LABELS)


def load_dataset(csv_path: str | Path) -> list[dict[str, str]]:
    """CSV dosyasını okur ve satır listesini döndürür."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"Veri seti dosyası bulunamadı: {csv_path}")

    records: list[dict[str, str]] = []
    with open(path, mode="r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"CSV başlığı okunamadı: {csv_path}")

        fieldnames = [fn.strip() for fn in reader.fieldnames]
        if "text" not in fieldnames or "label" not in fieldnames:
            raise ValueError(f"CSV 'text' ve 'label' sütunlarını içermelidir. Mevcut: {reader.fieldnames}")

        for idx, row in enumerate(reader, start=1):
            text = (row.get("text") or "").strip()
            label = (row.get("label") or "").strip().lower()
            if not text:
                raise ValueError(f"Satır {idx}: 'text' alanı boş olamaz.")
            if label not in VALID_LABELS:
                raise ValueError(f"Satır {idx}: Geçersiz duygu etiketi '{label}'. Geçerli: {VALID_LABELS}")
            records.append({"text": text, "label": label})

    if not records:
        raise ValueError(f"CSV dosyası hiç veri satırı içermiyor: {csv_path}")

    return records


def validate_dataset(data: list[dict[str, str]]) -> dict[str, int]:
    """Veri setini doğrular ve sınıf dağılımını döndürür."""
    if not data:
        raise ValueError("Veri seti boş.")

    counts: dict[str, int] = {lbl: 0 for lbl in ORDERED_LABELS}
    for item in data:
        lbl = item["label"]
        if lbl not in counts:
            raise ValueError(f"Bilinmeyen etiket: {lbl}")
        counts[lbl] += 1

    return counts


def calculate_metrics(
    y_true: list[str],
    y_pred: list[str],
    labels: list[str] | None = None,
) -> dict[str, Any]:
    """Saf Python ile Accuracy, Macro Precision, Macro Recall, Macro F1 ve Confusion Matrix hesaplar."""
    if len(y_true) != len(y_pred):
        raise ValueError(f"y_true ({len(y_true)}) ve y_pred ({len(y_pred)}) boyutları eşit olmalıdır.")

    target_labels = labels or ORDERED_LABELS
    label_to_idx = {lbl: idx for idx, lbl in enumerate(target_labels)}
    num_classes = len(target_labels)

    # 3x3 Confusion Matrix: [true_idx][pred_idx]
    cm = [[0 for _ in range(num_classes)] for _ in range(num_classes)]

    total_samples = len(y_true)
    if total_samples == 0:
        return {
            "accuracy": 0.0,
            "macro_precision": 0.0,
            "macro_recall": 0.0,
            "macro_f1": 0.0,
            "confusion_matrix": cm,
            "class_metrics": {},
        }

    correct_predictions = 0
    for yt, yp in zip(y_true, y_pred):
        if yt not in label_to_idx:
            raise ValueError(f"Geçersiz gerçek etiket: '{yt}'")
        if yp not in label_to_idx:
            raise ValueError(f"Geçersiz tahmin etiketi: '{yp}'")

        t_idx = label_to_idx[yt]
        p_idx = label_to_idx[yp]
        cm[t_idx][p_idx] += 1
        if yt == yp:
            correct_predictions += 1

    accuracy = correct_predictions / total_samples

    class_metrics: dict[str, dict[str, float]] = {}
    precisions: list[float] = []
    recalls: list[float] = []
    f1s: list[float] = []

    for i, lbl in enumerate(target_labels):
        tp = cm[i][i]
        fp = sum(cm[k][i] for k in range(num_classes) if k != i)
        fn = sum(cm[i][k] for k in range(num_classes) if k != i)

        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = (2 * prec * rec) / (prec + rec) if (prec + rec) > 0 else 0.0

        precisions.append(prec)
        recalls.append(rec)
        f1s.append(f1)

        class_metrics[lbl] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }

    macro_precision = sum(precisions) / num_classes if num_classes > 0 else 0.0
    macro_recall = sum(recalls) / num_classes if num_classes > 0 else 0.0
    macro_f1 = sum(f1s) / num_classes if num_classes > 0 else 0.0

    return {
        "accuracy": round(accuracy, 4),
        "macro_precision": round(macro_precision, 4),
        "macro_recall": round(macro_recall, 4),
        "macro_f1": round(macro_f1, 4),
        "confusion_matrix": cm,
        "class_metrics": class_metrics,
    }


def evaluate_rule_based(
    data: list[dict[str, str]],
    scorer: RuleBasedTurkishScorer | None = None,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    """RuleBasedTurkishScorer ile veri setini değerlendirir."""
    eval_scorer = scorer or RuleBasedTurkishScorer()
    y_true: list[str] = []
    y_pred: list[str] = []
    errors: list[dict[str, Any]] = []

    for idx, item in enumerate(data, start=1):
        content_id = f"eval-rule-{idx:03d}"
        text = item["text"]
        true_label = item["label"]

        content = ContentInput(id=content_id, text=text)
        result = eval_scorer.analyze(content)
        pred_label = result.sentiment.label

        y_true.append(true_label)
        y_pred.append(pred_label)

        if pred_label != true_label:
            errors.append({
                "content_id": content_id,
                "text": text,
                "true_label": true_label,
                "predicted_label": pred_label,
                "scorer": "rule_based",
            })

    metrics = calculate_metrics(y_true, y_pred)
    return metrics, errors


def evaluate_berturk(
    data: list[dict[str, str]],
    scorer: BerturkTurkishScorer | None = None,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], str | None]:
    """BerturkTurkishScorer ile veri setini değerlendirir.

    Model yüklenemezse veya fallback modundaysa sahte metrik üretmez;
    metrik olarak None döner ve hata nedenini açıklar.
    """
    eval_scorer = scorer or BerturkTurkishScorer()

    # Modelin yüklenip yüklenemediğini kontrol et
    info = eval_scorer.get_info()
    if info.fallback or not eval_scorer._is_loaded:
        reason = info.fallback_reason or eval_scorer._load_error or "BERTurk modeli yüklenemedi / kullanılamıyor"
        logger.warning("BERTurk değerlendirmesi yapılamadı (Model hazır değil): %s", reason)
        return None, [], reason

    y_true: list[str] = []
    y_pred: list[str] = []
    errors: list[dict[str, Any]] = []

    for idx, item in enumerate(data, start=1):
        content_id = f"eval-bert-{idx:03d}"
        text = item["text"]
        true_label = item["label"]

        try:
            content = ContentInput(id=content_id, text=text)
            result = eval_scorer.analyze(content)

            # Eğer inference sırasında beklenmedik şekilde fallback'e düştüyse
            if result.scorer and result.scorer.fallback:
                reason = result.scorer.fallback_reason or "Inference sırasında fallback devreye girdi."
                logger.warning("BERTurk inference sırasında fallback algılandı: %s", reason)
                return None, [], reason

            pred_label = result.sentiment.label
            y_true.append(true_label)
            y_pred.append(pred_label)

            if pred_label != true_label:
                errors.append({
                    "content_id": content_id,
                    "text": text,
                    "true_label": true_label,
                    "predicted_label": pred_label,
                    "scorer": "berturk",
                })
        except Exception as exc:
            reason = f"Örnek {content_id} çıkarımında hata oluştu ({exc.__class__.__name__}: {exc})"
            logger.error("BERTurk çıkarım hatası: %s", reason)
            return None, [], reason

    metrics = calculate_metrics(y_true, y_pred)
    return metrics, errors, None


def write_metrics(output_path: str | Path, metrics_payload: dict[str, Any]) -> None:
    """Metrik sonuçlarını JSON dosyasına yazar."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode="w", encoding="utf-8") as f:
        json.dump(metrics_payload, f, ensure_ascii=False, indent=2)
    logger.info("Metrikler yazıldı: %s", path)


def write_errors(output_path: str | Path, errors: list[dict[str, Any]]) -> None:
    """Yanlış tahmin dökümünü CSV dosyasına yazar."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = ["content_id", "text", "true_label", "predicted_label", "scorer"]
    with open(path, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for err in errors:
            writer.writerow(err)
    logger.info("Yanlış tahminler yazıldı (%d satır): %s", len(errors), path)


def run_evaluation(
    dataset_path: str | Path = "data/evaluation_sentiment.csv",
    artifacts_dir: str | Path = "artifacts",
    include_berturk: bool = True,
    berturk_scorer: BerturkTurkishScorer | None = None,
    rule_scorer: RuleBasedTurkishScorer | None = None,
) -> dict[str, Any]:
    """Tüm değerlendirme akışını yöneten ana fonksiyon."""
    logger.info("Değerlendirme başlatılıyor: %s", dataset_path)
    data = load_dataset(dataset_path)
    dist = validate_dataset(data)

    logger.info("Veri seti doğrulandı. Toplam örnek: %d", len(data))
    logger.info("Sınıf dağılımı: %s", dist)

    # 1. Rule-based Değerlendirme
    logger.info("RuleBasedTurkishScorer değerlendiriliyor...")
    rule_metrics, rule_errors = evaluate_rule_based(data, scorer=rule_scorer)
    logger.info("Rule-based Accuracy: %.4f | Macro F1: %.4f", rule_metrics["accuracy"], rule_metrics["macro_f1"])

    # 2. BERTurk Değerlendirme
    berturk_metrics: dict[str, Any] | None = None
    berturk_errors: list[dict[str, Any]] = []
    berturk_reason: str | None = None

    if include_berturk:
        logger.info("BerturkTurkishScorer değerlendiriliyor...")
        berturk_metrics, berturk_errors, berturk_reason = evaluate_berturk(data, scorer=berturk_scorer)
        if berturk_metrics is not None:
            logger.info("BERTurk Accuracy: %.4f | Macro F1: %.4f", berturk_metrics["accuracy"], berturk_metrics["macro_f1"])
        else:
            logger.warning("BERTurk metrikleri üretilemedi (Gerekçe: %s)", berturk_reason)

    all_errors = rule_errors + berturk_errors

    artifacts_path = Path(artifacts_dir)
    artifacts_path.mkdir(parents=True, exist_ok=True)
    metrics_file = artifacts_path / "evaluation_metrics.json"
    errors_file = artifacts_path / "evaluation_errors.csv"

    payload: dict[str, Any] = {
        "evaluation_timestamp": datetime.now(timezone.utc).isoformat(),
        "dataset_type": "synthetic",
        "dataset_warning": "Bu veri seti kurgusal ve sentetik bir test setidir; gerçek sosyal medya benchmark'ı veya genel geçer model performans iddiası değildir.",
        "sample_count": len(data),
        "class_distribution": dist,
        "metrics": {
            "rule_based": rule_metrics,
            "berturk": berturk_metrics,
        },
        "errors_file": str(errors_file.as_posix()),
        "berturk_status": {
            "loaded": berturk_metrics is not None,
            "reason": berturk_reason,
        },
    }

    write_metrics(metrics_file, payload)
    write_errors(errors_file, all_errors)

    return payload


if __name__ == "__main__":
    run_evaluation()
