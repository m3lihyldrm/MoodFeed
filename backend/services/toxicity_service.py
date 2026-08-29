"""MoodFeed Toxicity & Meta-Signal Risk Analyzer Service.

Analyzes text for abusive / toxic dictionary signals combined with
user and message meta-signals (account age, posting frequency, repetition ratio, keyword stuffing)
to detect spam, bot, and toxicity risks.
"""

from __future__ import annotations

import re
from typing import Any, Literal


def clamp_val(value: float) -> float:
    return round(max(0.0, min(1.0, value)), 3)


class ToxicityAnalyzer:
    """Toksisite ve meta sinyal tabanlı spam/bot risk analizcisi."""

    toxic_words = frozenset({"aptal", "salak", "iğrenç", "defol", "rezil", "senden nefret", "öldür", "tehdit"})
    toxic_context_words = frozenset({"saldırgan", "hakaret", "küfür", "zorbalık", "şiddet", "taciz"})

    def _analyze_words(self, content: str) -> float:
        """Kelime sözlüğü analizi ile toksisite skoru hesaplar."""
        normalized = content.lower()
        toxic_hits = sum(1 for word in self.toxic_words if word in normalized)
        return clamp_val(toxic_hits * 0.35)

    def _calculate_repetition_ratio(self, content: str) -> float:
        """Metin içi kelime tekrar oranını hesaplar (bot/spam sinyali)."""
        tokens = [t for t in re.findall(r"\w+", content.lower()) if len(t) > 2]
        if not tokens:
            return 0.0
        unique_tokens = set(tokens)
        return clamp_val(1.0 - (len(unique_tokens) / len(tokens)))

    def _detect_keyword_stuffing(self, content: str) -> bool:
        """Anahtar kelime yığınlama (keyword stuffing) tespiti."""
        tokens = [t for t in re.findall(r"\w+", content.lower()) if len(t) > 2]
        if not tokens:
            return False
        from collections import Counter
        counts = Counter(tokens)
        max_frequency = max(counts.values()) if counts else 0
        return max_frequency >= 4 and (max_frequency / len(tokens)) > 0.3

    def analyze(self, content: str, user_metadata: dict[str, Any] | None = None) -> dict[str, Any]:
        """Meta sinyaller ve kelime sözlüğü ile kapsamlı toksisite & bot analizi.

        Meta sinyaller:
        - account_age_days: Hesap yaşı (<7 gün = spam risk +0.3)
        - posts_per_hour: Paylaşım sıklığı (>10/saat = spam risk +0.4)
        - repetition_ratio: Tekrar oranı (>0.5 = bot risk +0.3)
        - keyword_stuffing: Anahtar kelime yığınlama (+0.2)
        """
        metadata = user_metadata or {}

        # Kelime sözlüğü analizi (mevcut)
        word_score = self._analyze_words(content)

        # Meta sinyaller
        account_age = int(metadata.get("account_age_days", 365))
        posts_per_hour = float(metadata.get("posts_per_hour", 1.0))

        if "repetition_ratio" in metadata:
            repetition_ratio = float(metadata["repetition_ratio"])
        else:
            repetition_ratio = self._calculate_repetition_ratio(content)

        keyword_stuffing = bool(metadata.get("keyword_stuffing", False) or self._detect_keyword_stuffing(content))

        # Spam/bot risk skorları
        spam_score = 0.0
        if account_age < 7:
            spam_score += 0.3
        if posts_per_hour > 10:
            spam_score += 0.4
        if repetition_ratio > 0.5:
            spam_score += 0.3
        if keyword_stuffing:
            spam_score += 0.2

        spam_score_clamped = min(round(spam_score, 3), 1.0)
        bot_risk: Literal["low", "medium", "high"] = "high" if spam_score_clamped > 0.5 else ("medium" if spam_score_clamped > 0.3 else "low")

        return {
            "toxicity_score": word_score,
            "spam_score": spam_score_clamped,
            "bot_risk": bot_risk,
            "meta_signals": {
                "account_age_days": account_age,
                "posts_per_hour": posts_per_hour,
                "repetition_ratio": repetition_ratio,
                "keyword_stuffing": keyword_stuffing,
                "spam_score": spam_score_clamped,
                "bot_risk": bot_risk,
            },
        }


# Global analyzer singleton
toxicity_analyzer = ToxicityAnalyzer()
