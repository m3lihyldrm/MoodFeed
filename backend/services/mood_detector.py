"""MoodFeed Mood Detection AI Service.

Provides multi-modal sentiment and 6-class mood classification:
- Calm (huzurlu, dengeli, bilim, doğa, sanat, dingin)
- Happy (mutlu, sevinçli, ilham verici, başarı, coşku)
- Neutral (tarafsız, bilgilendirici, standart haber akışı)
- Anxious (endişeli, kaygılı, risk, uyarı, belirsizlik)
- Sad (üzgün, hüzünlü, kayıp, yas, keder)
- Angry (öfkeli, tepkili, skandal, adaletsizlik, hiddet)

Outputs:
- mood_score: float in range [-1.0, 1.0] (-1.0 negative to 1.0 positive)
- mood_label: Literal["calm", "happy", "neutral", "anxious", "sad", "angry"]
- mood_distribution: dict[str, float] with probability / affinity across all 6 moods + confidence
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

# 6 Standard Mood Labels
MoodLabel = Literal["calm", "happy", "neutral", "anxious", "sad", "angry"]

# Comprehensive Turkish Lexicons for Emotion & Mood Detection
CALM_KEYWORDS = {
    "huzur", "sakin", "dingin", "denge", "meditasyon", "doğa", "sanat", "kültür",
    "sessizlik", "barış", "ferah", "dinlendirici", "edebiyat", "şiir", "keşif",
    "bilimsel", "uzay", "arkeoloji", "koruma", "yeşil", "çevre", "park", "bahçe",
    "yürüyüş", "rahatlatıcı", "uyum", "hoşgörü", "temiz hava", "nefes", "manzara",
    "akustik", "kitap", "müze", "sergi", "konser", "klasik", "tatil", "sessiz",
    "şifa", "doğal", "sağlıklı yaşam", "bitki", "yoga", "sabır", "mola", "huzurlu"
}

HAPPY_KEYWORDS = {
    "mutlu", "harika", "sevinç", "güzel", "tebrik", "başarı", "umut", "muhteşem",
    "şahane", "aşk", "sevgi", "keyif", "kutlu", "zafer", "teşekkür", "mükemmel",
    "bayıldım", "şükür", "tatlı", "gülümsüyorum", "aydınlık", "gelişme", "dostluk",
    "iyilik", "sevindirici", "hoş", "neşeli", "gurur", "coşku", "harikaydı", "mutluluk",
    "bereket", "şans", "pozitif", "kazandık", "rekor", "bayram", "şenlik", "kutlama",
    "ödül", "şampiyon", "müjde", "sevindirdi", "parlıyor", "kahkaha", "şen", "umutlu"
}

SAD_KEYWORDS = {
    "üzgün", "hüzün", "keder", "acı", "kayıp", "vefat", "maalesef", "mutsuz",
    "ağlamak", "gözyaşı", "yıkım", "yalnız", "çaresiz", "özledim", "yıkıldım",
    "depresyon", "hastalık", "kırgın", "veda", "canım acıyor", "kahroldum", "yazık",
    "perişan", "yas", "hüzünlü", "matem", "karanlık", "çöküş", "kaybettik", "kederli",
    "hayatını kaybetti", "can kaybı", "vefat etti", "cenaze", "şehit", "ölen", "öldü",
    "kahreden", "acı haber", "trajik", "acıklı", "taziye", "kaybettik"
}

ANGRY_KEYWORDS = {
    "öfke", "kızgın", "nefret", "rezalet", "berbat", "iğrenç", "düşman", "ceza",
    "lanet", "saldırı", "terbiyesiz", "haksızlık", "tepki", "rezillik", "küstah",
    "çıldıracağım", "saçmalık", "şerefsiz", "aptal", "ahmak", "yalan", "dolandırıcı",
    "ihanet", "skandal", "öfkeli", "hiddet", "isyan", "yuh", "utanmaz", "bıktık",
    "kınadı", "sert tepki", "provokasyon", "gerginlik", "kavga", "çatışma", "suçlama",
    "vurgun", "yolsuzluk", "istifa", "protesto", "isyan etti", "öfke kustu"
}

ANXIOUS_KEYWORDS = {
    "endişe", "kaygı", "korku", "panik", "risk", "tehlike", "stres", "tehdit",
    "alarm", "şüphe", "belirsizlik", "telaş", "tedirgin", "korkunç", "korkuyorum",
    "güvensiz", "dehşet", "vahim", "endişeliyim", "acaba", "bunalım", "sıkıntı",
    "facia", "kriz", "felaket", "panikledim", "tedirginlik", "korkutucu", "uyarı",
    "dikkat", "acil durum", "deprem", "fırtına", "salgın", "enflasyon", "zam", "zamlar",
    "tehlikeli", "tehlike altında", "kara tablo", "kara haber", "baskı", "endişeli"
}


class MoodDetector:
    """Mood & Emotion Detector with Hugging Face API & 6-class Turkish Lexicon Scoring."""

    def __init__(self) -> None:
        self.hf_api_token = (
            os.getenv("HUGGINGFACE_API_KEY")
            or os.getenv("HUGGINGFACE_API_TOKEN")
            or os.getenv("HF_TOKEN")
        )
        self.model_name = os.getenv("HF_MODEL_NAME", "cardiffnlp/twitter-xlm-roberta-base-sentiment")
        self.api_url = f"https://api-inference.huggingface.co/models/{self.model_name}"
        self.client = httpx.Client(timeout=4.0)

    def _normalize_text(self, text: str) -> str:
        t = text.lower()
        t = t.replace("İ", "i").replace("I", "ı")
        t = re.sub(r"https?://\S+", "", t)
        t = re.sub(r"[@#][a-zA-Z0-9_çğıöşüÇĞİÖŞÜ]+", "", t)
        return t.strip()

    def _detect_via_lexicon(
        self,
        text: str,
        title: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """High-precision 6-class Turkish emotion, mood score, and mood distribution analyzer."""
        full_text = f"{title}. {text}" if title and title not in text else text
        clean = self._normalize_text(full_text)
        words = set(re.findall(r"\b[a-zA-ZçğıöşüÇĞİÖŞÜ]+\b", clean))

        calm_count = len(words.intersection(CALM_KEYWORDS))
        happy_count = len(words.intersection(HAPPY_KEYWORDS))
        sad_count = len(words.intersection(SAD_KEYWORDS))
        angry_count = len(words.intersection(ANGRY_KEYWORDS))
        anxious_count = len(words.intersection(ANXIOUS_KEYWORDS))

        # Check multi-word keyword phrases
        for phrase in ("hayatını kaybetti", "can kaybı", "acı haber", "vefat etti", "şehit oldu"):
            if phrase in clean:
                sad_count += 2
        for phrase in ("sert tepki", "öfke kustu", "istifa çağrısı", "isyan etti"):
            if phrase in clean:
                angry_count += 2
        for phrase in ("alarm verildi", "acil durum", "deprem uyarısı", "kara tablo", "endişe yarattı"):
            if phrase in clean:
                anxious_count += 2
        for phrase in ("tarihi rekor", "büyük başarı", "şampiyon oldu", "gururlandırdı", "umut oldu"):
            if phrase in clean:
                happy_count += 2
        for phrase in ("doğal yaşam", "yeşil alan", "kültür sanat", "bilim dünyası", "huzur veren"):
            if phrase in clean:
                calm_count += 2

        # Category contextual affinity
        cat_lower = (category or "").lower()
        if "sanat" in cat_lower or "kültür" in cat_lower or "çevre" in cat_lower or "bilim" in cat_lower:
            calm_count += 1
        elif "spor" in cat_lower:
            if happy_count > 0:
                happy_count += 1

        total_emotional = calm_count + happy_count + sad_count + angry_count + anxious_count

        # Compute raw weights
        raw_calm = 0.15 + (calm_count * 0.4)
        raw_happy = 0.10 + (happy_count * 0.45)
        raw_sad = 0.05 + (sad_count * 0.45)
        raw_angry = 0.05 + (angry_count * 0.45)
        raw_anxious = 0.08 + (anxious_count * 0.4)

        if total_emotional == 0:
            raw_neutral = 0.65
        else:
            raw_neutral = max(0.12, 0.55 - (total_emotional * 0.1))

        # Category bonus for calm when content is low conflict
        if cat_lower in ("kültür", "sanat", "çevre", "bilim", "eğitim") and sad_count == 0 and angry_count == 0 and anxious_count == 0:
            raw_calm += 0.25

        total_weights = raw_calm + raw_happy + raw_sad + raw_angry + raw_anxious + raw_neutral

        # Normalize distribution
        p_calm = round(raw_calm / total_weights, 3)
        p_happy = round(raw_happy / total_weights, 3)
        p_sad = round(raw_sad / total_weights, 3)
        p_angry = round(raw_angry / total_weights, 3)
        p_anxious = round(raw_anxious / total_weights, 3)
        p_neutral = round(max(0.0, 1.0 - (p_calm + p_happy + p_sad + p_angry + p_anxious)), 3)

        scores_map = {
            "calm": p_calm,
            "happy": p_happy,
            "neutral": p_neutral,
            "anxious": p_anxious,
            "sad": p_sad,
            "angry": p_angry,
        }

        dominant_label = max(scores_map, key=scores_map.get)  # type: ignore[arg-type]
        confidence = scores_map[dominant_label]

        # Calculate continuous mood_score (-1.0 to 1.0)
        pos_signal = p_happy * 1.0 + p_calm * 0.6
        neg_signal = p_sad * 0.8 + p_angry * 1.0 + p_anxious * 0.7
        mood_score = round(max(-1.0, min(1.0, pos_signal - neg_signal)), 2)

        # Negativity & toxicity
        negativity = round(min(1.0, (sad_count * 0.25) + (angry_count * 0.3) + (anxious_count * 0.2) + (0.05 if dominant_label in ("sad", "angry", "anxious") else 0.02)), 2)
        toxicity = round(min(1.0, (angry_count * 0.28) + (0.1 if dominant_label == "angry" else 0.0)), 2)

        if mood_score > 0.15:
            sentiment_label = "positive"
        elif mood_score < -0.15:
            sentiment_label = "negative"
        else:
            sentiment_label = "neutral"

        return {
            "mood_score": mood_score,
            "mood_label": dominant_label,
            "mood_distribution": {
                "calm": p_calm,
                "happy": p_happy,
                "neutral": p_neutral,
                "anxious": p_anxious,
                "sad": p_sad,
                "angry": p_angry,
                "confidence": confidence,
            },
            "sentiment": {
                "label": sentiment_label,
                "score": round(max(pos_signal, neg_signal, p_neutral), 2),
            },
            "negativity_score": negativity,
            "toxicity_score": toxicity,
            "source": "lexicon_6class",
        }

    def _detect_via_hf(self, text: str, title: str | None = None) -> dict[str, Any] | None:
        """Calls Hugging Face Inference API if token is configured."""
        token = (
            os.getenv("HUGGINGFACE_API_KEY")
            or os.getenv("HUGGINGFACE_API_TOKEN")
            or os.getenv("HF_TOKEN")
        )
        if not token:
            return None

        try:
            full_text = f"{title}. {text}" if title else text
            headers = {"Authorization": f"Bearer {token}"}
            payload = {"inputs": full_text[:500]}
            resp = self.client.post(self.api_url, json=payload, headers=headers)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and len(data) > 0:
                    scores = data[0] if isinstance(data[0], list) else data
                    score_map = {item["label"].lower(): item["score"] for item in scores if "label" in item}
                    pos = score_map.get("positive", score_map.get("label_2", 0.0))
                    neg = score_map.get("negative", score_map.get("label_0", 0.0))
                    neu = score_map.get("neutral", score_map.get("label_1", 0.0))

                    lex = self._detect_via_lexicon(text, title=title)
                    mood_score = round(pos - neg, 2)

                    if mood_score > 0.25:
                        mood_label = "happy" if lex["mood_distribution"]["happy"] >= lex["mood_distribution"]["calm"] else "calm"
                        sentiment_label = "positive"
                    elif mood_score < -0.25:
                        mood_label = lex["mood_label"] if lex["mood_label"] in ("sad", "angry", "anxious") else "sad"
                        sentiment_label = "negative"
                    else:
                        mood_label = lex["mood_label"] if lex["mood_distribution"]["confidence"] > 0.45 else "neutral"
                        sentiment_label = "neutral"

                    dist = lex["mood_distribution"]
                    return {
                        "mood_score": mood_score,
                        "mood_label": mood_label,
                        "mood_distribution": dist,
                        "sentiment": {"label": sentiment_label, "score": round(max(pos, neg, neu), 2)},
                        "negativity_score": round(neg, 2),
                        "toxicity_score": round(neg * 0.6 if mood_label == "angry" else neg * 0.2, 2),
                        "source": "huggingface",
                    }
        except Exception as e:
            logger.debug(f"HF inference error, using fallback: {e}")
        return None

    def detect_mood(
        self,
        text: str,
        title: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Detects 6-class mood, sentiment, continuous mood score, and confidence distribution."""
        if not text and not title:
            return {
                "mood_score": 0.0,
                "mood_label": "neutral",
                "mood_distribution": {
                    "calm": 0.1,
                    "happy": 0.1,
                    "neutral": 0.6,
                    "anxious": 0.1,
                    "sad": 0.05,
                    "angry": 0.05,
                    "confidence": 0.6,
                },
                "sentiment": {"label": "neutral", "score": 0.5},
                "negativity_score": 0.0,
                "toxicity_score": 0.0,
                "source": "empty",
            }

        # 1. Try Hugging Face API if available
        hf_result = self._detect_via_hf(text, title=title)
        if hf_result:
            return hf_result

        # 2. Use 6-Class Turkish Rule-Based Lexicon Scorer
        return self._detect_via_lexicon(text, title=title, category=category)

    async def detect_mood_async(
        self,
        text: str,
        title: str | None = None,
        category: str | None = None,
    ) -> dict[str, Any]:
        """Async variant of detect_mood."""
        return self.detect_mood(text, title=title, category=category)


# Global singleton instance
mood_detector = MoodDetector()
MoodDetectionService = MoodDetector


def detect_mood(
    text: str = "",
    title: str | None = None,
    category: str | None = None,
) -> dict[str, Any]:
    """Top-level helper function for 6-class mood detection."""
    return mood_detector.detect_mood(text=text, title=title, category=category)

