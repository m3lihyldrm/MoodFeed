"""MoodFeed Algorithmic Explanation Service.

Generates 3-tiered explanations (card summary, drawer explanation, advanced formula details)
strictly adhering to neutral linguistic framing and transparent user control.
"""

from __future__ import annotations

from typing import Any
from backend.models import RankedContent


class ExplanationService:
    """Production Explanation Generator Service."""

    def generate_explanation(self, item: RankedContent, profile_name: str = "balanced") -> dict[str, Any]:
        """Produces structured 3-tier explanation for a given ranked content item."""
        diff = item.original_rank - item.new_rank

        # Tier 1: Card Summary
        if diff > 0:
            card_summary = f"Akış çeşitliliği ve yapıcı içerik sinyali nedeniyle {diff} sıra öne taşındı."
        elif diff < 0:
            card_summary = f"Yoğun negatiflik veya toksisite sinyali nedeniyle {abs(diff)} sıra geriye çekildi."
        else:
            card_summary = "İçerik sinyalleri dengeli olduğu için başlangıç sırası korundu."

        # Tier 2: 4-Pillar Drawer Explanation
        if item.toxicity_score > 0.3:
            observed = f"Metinde belirgin gergin veya saldırgan dil sinyali ({item.toxicity_score:.2f}) gözlendi."
            action = f"Toksisite filtresi katsayısı ağırlığıyla sıralaması #{item.new_rank} olarak ayarlandı."
        elif item.negativity_score > 0.5:
            observed = f"Metinde yüksek şikayet ve stres sinyali ({item.negativity_score:.2f}) tespit edildi."
            action = f"Yoğun negatiflik maruziyetini hafifletmek için sıralamada dengelendi."
        else:
            observed = f"Metinde düşük gerginlik ve yapıcı paylaşım sinyali (Negatiflik: {item.negativity_score:.2f}) görüldü."
            action = "Akış dengesini korumak için üst sıralardaki konumu pekiştirildi."

        drawer_explanation = {
            "observed_signals": observed,
            "applied_rules": f"'{profile_name}' profili katsayıları ve çeşitlilik bonusu uygulandı.",
            "rank_change": f"#{item.original_rank} ➔ #{item.new_rank} (Fark: {diff:+d})",
            "user_controls": "Öneriyi Geri Al butonu ile dilediğiniz an orijinal sıraya dönebilirsiniz.",
            "limitation": "Bu açıklama sözlük tabanlı dilbilimsel metin sinyallerine dayanır; psikolojik veya klinik bir değerlendirme değildir.",
            "confidence_level": "high",
        }

        # Tier 3: Advanced Formula Details
        bd = item.score_breakdown
        formula_details = {
            "formula": "ranking_score = clamp(S_orig - W_tox*T - W_neg*N*R + W_div*D*R)",
            "breakdown": {
                "original_score": bd.original_score if bd else item.ranking_score,
                "toxicity_penalty": bd.toxicity_penalty if bd else 0.0,
                "negativity_penalty": bd.negativity_penalty if bd else 0.0,
                "diversity_bonus": bd.diversity_bonus if bd else 0.0,
                "final_score": bd.final_score if bd else item.ranking_score,
            },
            "algorithm_version": "1.2.0",
        }

        return {
            "content_id": item.content_id,
            "card_summary": card_summary,
            "drawer_explanation": drawer_explanation,
            "formula_details": formula_details,
        }


# Global explanation service instance
explanation_service = ExplanationService()
