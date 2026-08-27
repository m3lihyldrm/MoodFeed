import os
from dataclasses import dataclass
from typing import Protocol
from .models import AnalysisResult, ContentInput, ProfileMetadata, ProfileWeights, ScenarioMetadata, ScorerInfo, Sentiment

def clamp(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)

@dataclass(frozen=True)
class ScoreConfig:
    """MVP için merkezi ve değiştirilebilir katsayılar."""
    toxicity_penalty: float = 0.35
    negative_risk_penalty: float = 0.25
    diversity_bonus: float = 0.15

PROFILE_CONFIGS: dict[str, tuple[ScoreConfig, ProfileMetadata]] = {
    "balanced": (
        ScoreConfig(toxicity_penalty=0.35, negative_risk_penalty=0.25, diversity_bonus=0.15),
        ProfileMetadata(
            profile="balanced",
            profile_label="Dengeli",
            weights=ProfileWeights(toxicity=0.35, negativity=0.25, diversity=0.15),
            description="Standart duygu, toksisite ve risk dengesi.",
        ),
    ),
    "calmer": (
        ScoreConfig(toxicity_penalty=0.50, negative_risk_penalty=0.40, diversity_bonus=0.25),
        ProfileMetadata(
            profile="calmer",
            profile_label="Daha Sakin Akış",
            weights=ProfileWeights(toxicity=0.50, negativity=0.40, diversity=0.25),
            description="Toksisite ve olumsuzluk sinyallerine karşı daha hassas filtreleme.",
        ),
    ),
    "user_control": (
        ScoreConfig(toxicity_penalty=0.15, negative_risk_penalty=0.10, diversity_bonus=0.05),
        ProfileMetadata(
            profile="user_control",
            profile_label="Kullanıcı Kontrolü",
            weights=ProfileWeights(toxicity=0.15, negativity=0.10, diversity=0.05),
            description="Minimum algoritmik müdahale ile orijinal akışa en yakın sıralama.",
        ),
    ),
}

SCENARIO_CONFIGS: dict[str, ScenarioMetadata] = {
    "default": ScenarioMetadata(
        name="default",
        label="Varsayılan Demo",
        synthetic=False,
        notice=None,
    ),
    "high_negativity": ScenarioMetadata(
        name="high_negativity",
        label="Simüle Edilmiş Yüksek Olumsuzluk",
        synthetic=True,
        notice="Bu senaryo yalnızca jüri demosu için oluşturulmuştur; gerçek kullanıcı ruh hâlini veya klinik bir durumu temsil etmez.",
    ),
    "highNegativity": ScenarioMetadata(
        name="highNegativity",
        label="Simüle Edilmiş Yüksek Olumsuzluk",
        synthetic=True,
        notice="Bu senaryo yalnızca jüri demosu için oluşturulmuştur; gerçek kullanıcı ruh hâlini veya klinik bir durumu temsil etmez.",
    ),
    "high_toxicity": ScenarioMetadata(
        name="high_toxicity",
        label="Simüle Edilmiş Yüksek Toksisite",
        synthetic=True,
        notice="Bu senaryo yüksek toksisite filtreleme davranışını doğrulamak için tasarlanmıştır.",
    ),
    "highToxicity": ScenarioMetadata(
        name="highToxicity",
        label="Simüle Edilmiş Yüksek Toksisite",
        synthetic=True,
        notice="Bu senaryo yüksek toksisite filtreleme davranışını doğrulamak için tasarlanmıştır.",
    ),
    "balanced_calmer": ScenarioMetadata(
        name="balanced_calmer",
        label="Dengeli Sakin Akış",
        synthetic=True,
        notice="Bu senaryo sakinleştirici ve çeşitlilik bonuslu akış dengesini gösterir.",
    ),
    "balancedCalmer": ScenarioMetadata(
        name="balancedCalmer",
        label="Dengeli Sakin Akış",
        synthetic=True,
        notice="Bu senaryo sakinleştirici ve çeşitlilik bonuslu akış dengesini gösterir.",
    ),
}

class ContentScorer(Protocol):
    """BERTurk gibi gelecekteki model sağlayıcıları için sözleşme."""
    def analyze(self, content: ContentInput) -> AnalysisResult: ...
    def get_info(self) -> ScorerInfo: ...

class RuleBasedTurkishScorer:
    """Harici servis gerektirmeyen açıklanabilir Türkçe anahtar sözcük skorlayıcısı."""
    positive_words = frozenset({"harika", "güzel", "mutlu", "teşekkür", "destek", "umut", "başarı", "sevgi", "keyifli", "iyi"})
    negative_words = frozenset({"kötü", "üzgün", "nefret", "korku", "stres", "zor", "başarısız", "endişe", "sinir", "berbat"})
    toxic_words = frozenset({"aptal", "salak", "iğrenç", "defol", "rezil", "senden nefret", "öldür", "tehdit"})
    toxic_context_words = frozenset({"saldırgan", "hakaret", "küfür", "zorbalık", "şiddet", "taciz"})

    def get_info(self) -> ScorerInfo:
        return ScorerInfo(
            name="rule_based",
            label="Kural Tabanlı (Varsayılan ve Kararlı)",
            model_name=None,
            fallback=False,
            fallback_reason=None,
            mode="rule_based",
            is_experimental=False,
            loaded=True,
        )

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
        sentiment_desc = {"positive": "Olumlu duygu eğilimi algılandı.", "negative": "Olumsuz duygu eğilimi algılandı.", "neutral": "Belirgin bir duygu eğilimi algılanmadı."}[label]
        if toxicity > 0:
            toxic_desc = "Saldırgan ifade sinyalleri bulundu."
        elif any(word in normalized for word in self.toxic_context_words):
            toxic_desc = "Metin saldırgan içerikten söz ediyor; ancak doğrudan bir kişiye saldırı içermiyor."
        else:
            toxic_desc = "Saldırgan ifade sinyali bulunmadı."
        reasons = [
            f"[Kural Tabanlı Skorlama] {sentiment_desc}",
            toxic_desc,
            "Bu sonuç kural tabanlı bir prototip tahminidir; klinik değerlendirme değildir.",
        ]
        return AnalysisResult(
            content_id=content.id,
            text=content.text,
            sentiment=Sentiment(label=label, score=sentiment_score),
            toxicity_score=toxicity,
            negativity_score=negativity,
            reason=reasons,
            scorer=self.get_info(),
            title=content.title,
            url=content.url,
            source=content.source,
            author=content.author,
            category=content.category,
            published_at=content.published_at,
            image_url=content.image_url,
        )

    @staticmethod
    def _count_hits(text: str, vocabulary: frozenset[str]) -> int:
        return sum(1 for word in vocabulary if word in text)

def get_scorer(scorer_type: str | None = None) -> ContentScorer:
    """Seçilen veya MOODFEED_SCORER ortam değişkeninde belirtilen scorer sağlayıcısını döndürür."""
    mode = (scorer_type or os.getenv("MOODFEED_SCORER", "rule_based")).strip().lower()
    if mode == "berturk":
        from .berturk_scorer import BerturkTurkishScorer
        return BerturkTurkishScorer()
    return RuleBasedTurkishScorer()


MoodScorer = RuleBasedTurkishScorer
