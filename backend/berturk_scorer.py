import logging
import os
from typing import Any, Literal
from .models import AnalysisResult, ContentInput, ScorerInfo, Sentiment
from .scoring import ContentScorer, RuleBasedTurkishScorer, clamp

logger = logging.getLogger("moodfeed.berturk")

DEFAULT_BERTURK_MODEL = "Omar1010/bert-turkish-sentiment"

LABEL_MAPPING: dict[str, Literal["positive", "neutral", "negative"]] = {
    "positive": "positive",
    "olumlu": "positive",
    "pos": "positive",
    "label_2": "positive",
    "2": "positive",
    "negative": "negative",
    "olumsuz": "negative",
    "neg": "negative",
    "label_0": "negative",
    "0": "negative",
    "notr": "neutral",
    "nötr": "neutral",
    "neutral": "neutral",
    "notral": "neutral",
    "nötral": "neutral",
    "neu": "neutral",
    "label_1": "neutral",
    "1": "neutral",
}

def normalize_sentiment_label(raw_label: str) -> Literal["positive", "neutral", "negative"]:
    """Model etiketini standart positive, neutral veya negative değerine dönüştürür."""
    cleaned = str(raw_label).strip().lower()
    if cleaned in LABEL_MAPPING:
        return LABEL_MAPPING[cleaned]
    raise ValueError(f"Bilinmeyen model duygu etiketi: '{raw_label}'. Güvenli eşleme yapılamadı.")

class BerturkTurkishScorer:
    """Hazır fine-tuned BERTurk modeliyle Türkçe duygu analizi ve kural tabanlı fallback sağlayıcısı."""

    def __init__(
        self,
        model_name: str | None = None,
        fallback_scorer: RuleBasedTurkishScorer | None = None,
        pipeline_instance: Any | None = None,
    ) -> None:
        self.model_name = model_name or os.getenv("MOODFEED_BERTURK_MODEL", DEFAULT_BERTURK_MODEL)
        self.fallback_scorer = fallback_scorer or RuleBasedTurkishScorer()
        self._pipeline = pipeline_instance
        self._is_loaded = pipeline_instance is not None
        self._tried_loading = pipeline_instance is not None
        self._load_error: str | None = None
        self._last_inference_error: str | None = None

    def get_info(self) -> ScorerInfo:
        if not self._tried_loading:
            self._load_model()

        if self._is_loaded and not self._last_inference_error:
            return ScorerInfo(
                name="berturk",
                label="BERTurk",
                model_name=self.model_name,
                fallback=False,
                fallback_reason=None,
            )
        return ScorerInfo(
            name="rule_based_fallback",
            label="Kural Tabanlı Fallback",
            model_name=self.model_name,
            fallback=True,
            fallback_reason=self._last_inference_error or self._load_error or "Model kullanılamıyor",
        )

    def _load_model(self) -> bool:
        if self._tried_loading:
            return self._is_loaded
        self._tried_loading = True
        try:
            from transformers import pipeline  # type: ignore[import-untyped]
        except (ImportError, ModuleNotFoundError) as exc:
            self._load_error = f"Transformers/PyTorch kütüphaneleri bulunamadı ({exc.__class__.__name__})."
            logger.warning("BERTurk yüklenemedi: %s", self._load_error)
            return False

        try:
            logger.info("BERTurk modeli yükleniyor: %s", self.model_name)
            self._pipeline = pipeline(
                "text-classification",
                model=self.model_name,
                top_k=None,
                truncation=True,
                max_length=512,
            )
            self._is_loaded = True
            logger.info("BERTurk modeli başarıyla hazırlandı: %s", self.model_name)
            return True
        except Exception as exc:
            self._load_error = f"Model yüklenemedi ({exc.__class__.__name__})."
            logger.warning("BERTurk modeli hazırlanamadı: %s", self._load_error)
            return False

    def analyze(self, content: ContentInput) -> AnalysisResult:
        if not self._is_loaded and not self._load_model():
            return self._fallback_analysis(content, self._load_error or "Model kullanılamıyor")

        try:
            assert self._pipeline is not None
            raw_output = self._pipeline(content.text)
            scores_list: list[dict[str, Any]]
            if isinstance(raw_output, list) and raw_output and isinstance(raw_output[0], list):
                scores_list = raw_output[0]
            elif isinstance(raw_output, list):
                scores_list = raw_output
            else:
                raise ValueError(f"Beklenmeyen pipeline çıktı biçimi: {type(raw_output)}")

            best_label: Literal["positive", "neutral", "negative"] | None = None
            best_score = -1.0
            negative_prob = 0.0

            for item in scores_list:
                label_str = item.get("label", "")
                norm_label = normalize_sentiment_label(label_str)
                score_val = float(item.get("score", 0.0))

                if score_val > best_score:
                    best_score = score_val
                    best_label = norm_label

                if norm_label == "negative":
                    negative_prob = score_val

            if best_label is None:
                raise ValueError("Model çıktısından geçerli bir duygu etiketi üretilemedi.")

            sentiment_score = clamp(best_score)
            normalized_text = content.text.lower()
            toxic_hits = sum(1 for word in self.fallback_scorer.toxic_words if word in normalized_text)
            toxicity_score = clamp(toxic_hits * 0.35)
            negativity_score = clamp(negative_prob * 0.7 + toxicity_score * 0.3)

            tr_labels = {"positive": "olumlu", "negative": "olumsuz", "neutral": "nötr"}
            reasons = [
                f"BERTurk ({self.model_name}) ile %{sentiment_score * 100:.1f} güvenle {tr_labels[best_label]} duygu eğilimi algılandı.",
                "Saldırgan ifade sinyalleri bulundu." if toxicity_score > 0 else "Saldırgan ifade sinyali bulunmadı.",
                "Bu sonuç makine öğrenmesi destekli bir prototip tahminidir; klinik değerlendirme değildir.",
            ]

            return AnalysisResult(
                content_id=content.id,
                text=content.text,
                sentiment=Sentiment(label=best_label, score=sentiment_score),
                toxicity_score=toxicity_score,
                negativity_score=negativity_score,
                reason=reasons,
                scorer=self.get_info(),
            )
        except Exception as exc:
            err_msg = f"Inference hatası ({exc.__class__.__name__})"
            logger.warning("BERTurk çıkarımında hata oluştu, fallback çalıştırılıyor: %s", exc)
            self._last_inference_error = err_msg
            return self._fallback_analysis(content, err_msg)

    def _fallback_analysis(self, content: ContentInput, reason_note: str) -> AnalysisResult:
        result = self.fallback_scorer.analyze(content)
        result.reason.insert(0, f"[Fallback] BERTurk yerine kural tabanlı analiz uygulandı ({reason_note}).")
        result.scorer = ScorerInfo(
            name="rule_based_fallback",
            label="Kural Tabanlı Fallback",
            model_name=self.model_name,
            fallback=True,
            fallback_reason=self._last_inference_error or self._load_error or reason_note,
        )
        return result
