from .models import ContentInput, Interaction, RankedContent, RiskResult
from .scoring import ContentScorer, ScoreConfig, clamp

def calculate_spiral_risk(interactions: list[Interaction], window_size: int = 10) -> RiskResult:
    """Son etkileşimlerdeki olumsuzluk ortalaması ve oranından risk üretir."""
    recent = interactions[-window_size:]
    if not recent:
        return RiskResult(score=0.0, level="low")
    scores = [item.negativity_score for item in recent]
    score = clamp(0.6 * (sum(scores) / len(scores)) + 0.4 * (sum(score >= 0.5 for score in scores) / len(scores)))
    return RiskResult(score=score, level="high" if score >= 0.60 else "medium" if score >= 0.35 else "low")

def rerank(contents: list[ContentInput], interactions: list[Interaction], enabled: bool, scorer: ContentScorer, config: ScoreConfig) -> tuple[list[RankedContent], RiskResult]:
    """İçerikleri silmeden, risk seviyesine göre açıklanabilir biçimde sıralar."""
    risk = calculate_spiral_risk(interactions)
    prepared: list[RankedContent] = []
    for original_rank, content in enumerate(contents, start=1):
        result = scorer.analyze(content)
        if not enabled:
            result.reason.append("MoodFeed kapalı olduğu için orijinal akış sırası korundu.")
            prepared.append(
                RankedContent(
                    **result.model_dump(),
                    original_rank=original_rank,
                    new_rank=original_rank,
                    ranking_score=content.original_score,
                )
            )
            continue
        diversity = 1.0 if result.sentiment.label in {"positive", "neutral"} else 0.0
        score = clamp(content.original_score - config.toxicity_penalty * result.toxicity_score - config.negative_risk_penalty * result.negativity_score * risk.score + config.diversity_bonus * diversity * risk.score)
        prepared.append(RankedContent(**result.model_dump(), original_rank=original_rank, new_rank=original_rank, ranking_score=score))
    if not enabled:
        return prepared, risk
    ordered = sorted(prepared, key=lambda item: (-item.ranking_score, item.original_rank))
    for new_rank, item in enumerate(ordered, start=1):
        item.new_rank = new_rank
        item.reason.extend(_ranking_reasons(item, risk, new_rank))
    return ordered, risk

def _ranking_reasons(item: RankedContent, risk: RiskResult, new_rank: int) -> list[str]:
    reasons: list[str] = []
    if item.toxicity_score > 0:
        reasons.append("Toksisite sinyali nedeniyle sıralama puanı azaltıldı.")
    if risk.level == "high" and item.sentiment.label in {"positive", "neutral"}:
        reasons.append("Olumsuz içerik maruziyeti yüksek olduğu için dengeleyici içerik öne çıkarıldı.")
    if new_rank > item.original_rank:
        reasons.append("Olumsuzluk ve risk sinyalleri nedeniyle içerik geriye çekildi.")
    elif new_rank < item.original_rank:
        reasons.append("Akış çeşitliliğini artırmak için içerik öne çıkarıldı.")
    else:
        reasons.append("İçerik sırası mevcut sinyallerle korundu.")
    return reasons
