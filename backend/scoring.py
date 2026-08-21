from dataclasses import dataclass
from typing import Protocol
from .models import AnalysisResult, ContentInput, Sentiment

def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)

@dataclass(frozen=True)
class ScoreConfig:
    """MVP için merkezi ve değiştirilebilir katsayılar."""
    toxicity_penalty: float = 0.35
    negative_risk_penalty: float = 0.25
    diversity_bonus: float = 0.15

class ContentScorer(Protocol):
    """BERTurk gibi gelecekteki model sağlayıcıları için sözleşme."""
    def analyze(self, content: ContentInput) -> AnalysisResult: ...

class RuleBasedTurkishScorer:
    """Harici servis gerektirmeyen açıklanabilir Türkçe anahtar sözcük skorlayıcısı."""
    positive_words = frozenset({"harika", "güzel", "mutlu", "teşekkür", "destek", "umut", "başarı", "sevgi", "keyifli", "iyi"})
    negative_words = frozenset({"kötü", "üzgün", "nefret", "korku", "stres", "zor", "başarısız", "endişe", "sinir", "berbat"})
    toxic_words = frozenset({"aptal", "salak", "iğrenç", "defol", "rezil", "senden nefret", "öldür", "tehdit"})

    def analyze(self, content: ContentInput) -> AnalysisResult:
        normalized = content.text.lower()
        positive_hits = self._count_hits(normalized, self.positive_words)
        negative_hits = self._count_hits(normalized, self.negative_words)
        toxic_hits = self._count_hits(normalized, self.toxic_words)
        total_hits = positive_hits + negative_hits
        if negative_hits > positive_hits:
            label, sentiment_score = "negative", clamp(negative_hits / max(1, total_hits))
        elif positive_hits > negative_hits:
            label, sentiment_score = "positive", clamp(positive_hits / max(1, total_hits))
        else:
            label, sentiment_score = "neutral", 0.5
        toxicity = clamp(toxic_hits * 0.35)
        negativity = clamp((negative_hits / max(1, total_hits)) * 0.7 + toxicity * 0.3)
        reasons = [
            {"positive": "Olumlu duygu eğilimi algılandı.", "negative": "Olumsuz duygu eğilimi algılandı.", "neutral": "Belirgin bir duygu eğilimi algılanmadı."}[label],
            "Saldırgan ifade sinyalleri bulundu." if toxicity else "Saldırgan ifade sinyali bulunmadı.",
            "Bu sonuç kural tabanlı bir prototip tahminidir; klinik değerlendirme değildir.",
        ]
        return AnalysisResult(content_id=content.id, text=content.text, sentiment=Sentiment(label=label, score=sentiment_score), toxicity_score=toxicity, negativity_score=negativity, reason=reasons)

    @staticmethod
    def _count_hits(text: str, vocabulary: frozenset[str]) -> int:
        return sum(1 for word in vocabulary if word in text)
