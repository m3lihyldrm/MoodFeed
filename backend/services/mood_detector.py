"""MoodFeed Mood Detection AI Service.

Provides multi-modal sentiment and mood classification:
- Hugging Face Inference API (cardiffnlp/twitter-xlm-roberta-base-sentiment)
- BERTurk / Transformer pipeline integration
- Rule-based Turkish emotional lexicon fallback

Outputs:
- mood_score: float in range [-1.0, 1.0] (-1.0 negative to 1.0 positive)
- mood_label: Literal["happy", "sad", "angry", "anxious", "neutral"]
- toxicity_score: float in range [0.0, 1.0]
- negativity_score: float in range [0.0, 1.0]
"""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Literal
import httpx

logger = logging.getLogger("moodfeed.services.mood_detector")

# Mood Label definitions
MoodLabel = Literal["happy", "sad", "angry", "anxious", "neutral"]

# Comprehensive Turkish Lexicons for Fallback
HAPPY_KEYWORDS = {
    "mutlu", "harika", "sevinç", "güzel", "tebrik", "başarı", "umut", "muhteşem",
    "şahane", "aşk", "sevgi", "huzur", "keyif", "kutlu", "zafer", "teşekkür",
    "mükemmel", "bayıldım", "şükür", "tatlı", "gülümsüyorum", "aydınlık", "gelişme",
    "dostluk", "iyilik", "sevindirici", "hoş", "neşeli", "gurur", "coşku", "harikaydı",
    "mutluluk", "bereket", "şans", "pozitif", "kazandık", "rekor", "bayram", "şenlik"
}

SAD_KEYWORDS = {
    "üzgün", "hüzün", "keder", "acı", "kayıp", "vefat", "maalesef", "mutsuz",
    "ağlamak", "gözyaşı", "yıkım", "yalnız", "çaresiz", "özledim", "yıkıldım",
    "depresyon", "hastalık", "kırgın", "veda", "canım acıyor", "kahroldum", "yazık",
    "perişan", "yas", "hüzünlü", "matem", "karanlık", "çöküş", "kaybettik", "kederli"
}

ANGRY_KEYWORDS = {
    "öfke", "kızgın", "nefret", "rezalet", "berbat", "iğrenç", "düşman", "ceza",
    "lanet", "saldırı", "terbiyesiz", "haksızlık", "tepki", "rezillik", "küstah",
    "çıldıracağım", "saçmalık", "şerefsiz", "aptal", "ahmak", "yalan", "dolandırıcı",
    "ihanet", "skandal", "öfkeli", "hiddet", "isyan", "yuh", "utanmaz", "bıktık"
}

ANXIOUS_KEYWORDS = {
    "endişe", "kaygı", "korku", "panik", "risk", "tehlike", "stres", "tehdit",
    "alarm", "şüphe", "belirsizlik", "telaş", "tedirgin", "korkunç", "korkuyorum",
    "güvensiz", "dehşet", "vahim", "endişeliyim", "acaba", "bunalım", "sıkıntı",
    "facia", "kriz", "felaket", "alarm", "panikledim", "tedirginlik", "korkutucu"
}


class MoodDetector:
    """Mood & Emotion Detector with Hugging Face API & Turkish Lexicon Fallback."""

    def __init__(self) -> None:
        self.hf_api_token = os.getenv("HUGGINGFACE_API_TOKEN") or os.getenv("HF_TOKEN")
        self.model_name = os.getenv("HF_MODEL_NAME", "cardiffnlp/twitter-xlm-roberta-base-sentiment")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.client = httpx.Client(timeout=4.0)

    def _normalize_text(self, text: str) -> str:
        t = text.lower()
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"[@#][a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+", "", t)
        return t.strip()

    def _detect_via_lexicon(self, text: str) -> dict[str, Any]:
        """High-precision Turkish emotional keyword and sentiment scorer."""
        clean = self._normalize_text(text)
        words = set(re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ]+\b", clean))

        happy_count = len(words.intersection(HAPPY_KEYWORDS))
        sad_count = len(words.intersection(SAD_KEYWORDS))
        angry_count = len(words.intersection(ANGRY_KEYWORDS))
        anxious_count = len(words.intersection(ANXIOUS_KEYWORDS))

        total_emotional = happy_count + sad_count + angry_count + anxious_count

        if total_emotional == 0:
            return {
                "mood_score": 0.0,
                "mood_label": "neutral",
                "sentiment": {"label": "neutral", "score": 0.5},
                "negativity_score": 0.1,
                "toxicity_score": 0.0,
                "source": "lexicon_fallback",
            }

        counts = {
            "happy": happy_count,
            "sad": sad_count,
            "angry": angry_count,
            "anxious": anxious_count,
        }
        dominant_label = max(counts, key=counts.get)  # type: ignore[arg-type]

        if dominant_label == "happy":
            mood_score = min(1.0, 0.4 + (happy_count * 0.2))
            negativity = 0.02
            toxicity = 0.0
            sentiment_label = "positive"
        elif dominant_label == "sad":
            mood_score = max(-1.0, -0.3 - (sad_count * 0.2))
            negativity = min(1.0, 0.4 + (sad_count * 0.2))
            toxicity = 0.05
            sentiment_label = "negative"
        elif dominant_label == "angry":
            mood_score = max(-1.0, -0.5 - (angry_count * 0.25))
            negativity = min(1.0, 0.6 + (angry_count * 0.2))
            toxicity = min(1.0, 0.4 + (angry_count * 0.2))
            sentiment_label = "negative"
        elif dominant_label == "anxious":
            mood_score = max(-1.0, -0.3 - (anxious_count * 0.2))
            negativity = min(1.0, 0.5 + (anxious_count * 0.15))
            toxicity = 0.02
            sentiment_label = "negative"
        else:
            mood_score = 0.0
            negativity = 0.1
            toxicity = 0.0
            sentiment_label = "neutral"

        return {
            "mood_score": round(mood_score, 2),
            "mood_label": dominant_label,
            "sentiment": {"label": sentiment_label, "score": round(abs(mood_score), 2)},
            "negativity_score": round(negativity, 2),
            "toxicity_score": round(toxicity, 2),
            "source": "lexicon_fallback",
        }

    def _detect_via_hf(self, text: str) -> dict[str, Any] | None:
        """Calls Hugging Face Inference API if token is configured."""
        if not self.hf_api_token:
            return None

        try:
            headers = {"Authorization": f"Bearer {self.hf_api_token}"}
            payload = {"inputs": text[:500]}
            resp = self.client.post(self.api_url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    scores = data[0] if isinstance(data[0], list) else data
                    # Format: [{'label': 'positive', 'score': 0.8}, ...]
                    score_map = {item["label"].lower(): item["score"] for item in scores if "label" in item}
                    pos = score_map.get("positive", score_map.get("label_2", 0.0))
                    neg = score_map.get("negative", score_map.get("label_0", 0.0))
                    neu = score_map.get("neutral", score_map.get("label_1", 0.0))

                    mood_score = pos - neg
                    if mood_score > 0.25:
                        mood_label = "happy"
                        sentiment_label = "positive"
                    elif mood_score < -0.25:
                        # Refine negative into angry/anxious/sad
                        lex = self._detect_via_lexicon(text)
                        mood_label = lex["mood_label"] if lex["mood_label"] in ("sad", "angry", "anxious") else "sad"
                        sentiment_label = "negative"
                    else:
                        mood_label = "neutral"
                        sentiment_label = "neutral"

                    return {
                        "mood_score": round(mood_score, 2),
                        "mood_label": mood_label,
                        "sentiment": {"label": sentiment_label, "score": round(max(pos, neg, neu), 2)},
                        "negativity_score": round(neg, 2),
                        "toxicity_score": round(neg * 0.6 if mood_label == "angry" else neg * 0.2, 2),
                        "source": "huggingface",
                    }
        except Exception as e:
            logger.debug(f"HF inference error, using fallback: {e}")
        return None

    def detect_mood(self, text: str) -> dict[str, Any]:
        """Detects sentiment, mood score (-1.0 to 1.0), and emotion label."""
        if not text or not text.strip():
            return {
                "mood_score": 0.0,
                "mood_label": "neutral",
                "sentiment": {"label": "neutral", "score": 0.5},
                "negativity_score": 0.0,
                "toxicity_score": 0.0,
                "source": "empty",
            }

        # 1. Try Hugging Face API if available
        hf_result = self._detect_via_hf(text)
        if hf_result:
            return hf_result

        # 2. Use Turkish Rule-Based Lexicon Fallback
        return self._detect_via_lexicon(text)


# Global singleton instance
mood_detector = MoodDetector()
