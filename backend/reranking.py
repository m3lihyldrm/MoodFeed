from .models import ContentInput, Interaction, RankedContent, RiskResult, ScoreBreakdown
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
            breakdown = ScoreBreakdown(
                original_score=content.original_score,
                toxicity_penalty=0.0,
                negativity_penalty=0.0,
                diversity_bonus=0.0,
                final_score=content.original_score,
            )
            prepared.append(
                RankedContent(
                    **result.model_dump(),
                    original_rank=original_rank,
                    new_rank=original_rank,
                    ranking_score=content.original_score,
                    score_breakdown=breakdown,
                )
            )
            continue
        diversity = 1.0 if (result.sentiment.label in {"positive", "neutral"} and result.toxicity_score == 0.0) else 0.0
        tox_pen = round(config.toxicity_penalty * result.toxicity_score, 4)
        neg_pen = round(config.negative_risk_penalty * result.negativity_score * risk.score, 4)
        div_bon = round(config.diversity_bonus * diversity * risk.score, 4)
        score = clamp(content.original_score - tox_pen - neg_pen + div_bon)
        breakdown = ScoreBreakdown(
            original_score=content.original_score,
            toxicity_penalty=tox_pen,
            negativity_penalty=neg_pen,
            diversity_bonus=div_bon,
            final_score=score,
        )
        prepared.append(
            RankedContent(
                **result.model_dump(),
                original_rank=original_rank,
                new_rank=original_rank,
                ranking_score=score,
                score_breakdown=breakdown,
            )
        )
    if not enabled:
        return prepared, risk
    ordered = sorted(prepared, key=lambda item: (-item.ranking_score, item.original_rank))
    total_count = len(ordered)
    for new_rank, item in enumerate(ordered, start=1):
        item.new_rank = new_rank
        item.reason.extend(_ranking_reasons(item, risk, new_rank, total_count))
    return ordered, risk

def _ranking_reasons(item: RankedContent, risk: RiskResult, new_rank: int, total_count: int = 0) -> list[str]:
    reasons: list[str] = []

    if new_rank < item.original_rank:
        if item.sentiment.label == "negative":
            reasons.append("Çeşitlilik katsayısı nedeniyle sıralama puanı yükseldi; bu, içeriğin olumlu olduğu anlamına gelmez.")
        elif item.toxicity_score > 0:
            reasons.append("Sıralama puanı bağıl olarak yüksek kaldığı için öne çıktı; bu, içeriğin toksik olmadığı anlamına gelmez.")
        elif risk.level == "high" and item.sentiment.label in {"positive", "neutral"}:
            reasons.append("Olumsuz içerik maruziyeti yüksek olduğu için dengeleyici içerik öne çıkarıldı.")
        elif item.sentiment.label == "positive":
            reasons.append("Olumlu ve düşük riskli içerik olduğu için akış dengesini desteklemek üzere öne çıkarıldı.")
        else:
            reasons.append("Başlangıç sıralama puanı ve düşük risk sinyalleri nedeniyle öne çıktı.")
    elif new_rank > item.original_rank:
        if item.toxicity_score > 0 and (item.negativity_score > 0 or risk.score > 0):
            reasons.append("Toksisite, olumsuzluk ve risk sinyalleri nedeniyle içerik geriye çekildi.")
        elif item.toxicity_score > 0:
            reasons.append("Toksisite sinyali nedeniyle sıralama puanı düşürüldü ve içerik geriye çekildi.")
        elif item.negativity_score > 0 and risk.score > 0:
            reasons.append("Olumsuzluk ve risk sinyalleri nedeniyle içerik geriye çekildi.")
        elif item.negativity_score > 0:
            reasons.append("Olumsuzluk sinyali nedeniyle sıralama puanı düşürüldü ve içerik geriye çekildi.")
        else:
            reasons.append("Diğer içeriklerin bağıl sıralama puanları nedeniyle akış sırası güncellendi.")
    else:
        if item.toxicity_score > 0:
            if total_count > 0 and new_rank == total_count:
                reasons.append("Toksisite sinyali nedeniyle puan azaltıldı; içerik zaten son sırada olduğu için sıra değişmedi.")
            else:
                reasons.append("Toksisite sinyali nedeniyle puan azaltıldı; içerik mevcut sırasını korudu.")
        elif item.negativity_score > 0 and risk.score > 0:
            reasons.append("Olumsuzluk ve risk sinyalleri puanı etkiledi; içerik mevcut sırasını korudu.")
        else:
            reasons.append("İçerik sırası mevcut sinyallerle korundu.")

    return reasons
