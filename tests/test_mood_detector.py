"""Tests for Mood Detection AI service (Hugging Face + Turkish Lexicon Fallback)."""

import pytest
from backend.services.mood_detector import MoodDetector, mood_detector


def test_detect_mood_positive() -> None:
    result = mood_detector.detect_mood("Bugün harika ve çok mutluyum! Başarı kazandık.")
    assert result["mood_label"] == "happy"
    assert result["mood_score"] > 0.0
    assert result["sentiment"]["label"] == "positive"
    assert result["negativity_score"] < 0.2


def test_detect_mood_negative() -> None:
    result = mood_detector.detect_mood("Çok üzgünüm, büyük bir kayıp ve acı içindeyiz.")
    assert result["mood_label"] == "sad"
    assert result["mood_score"] < 0.0
    assert result["sentiment"]["label"] == "negative"
    assert result["negativity_score"] > 0.3


def test_detect_mood_angry() -> None:
    result = mood_detector.detect_mood("Bu rezalet ve haksızlık karşısında çok öfkeliyim, nefret ediyorum!")
    assert result["mood_label"] == "angry"
    assert result["mood_score"] < 0.0
    assert result["toxicity_score"] > 0.3


def test_detect_mood_anxious() -> None:
    result = mood_detector.detect_mood("Büyük bir panik ve felaket riski var, çok endişeliyim.")
    assert result["mood_label"] == "anxious"
    assert result["mood_score"] < 0.0


def test_detect_mood_neutral() -> None:
    result = mood_detector.detect_mood("Bugün toplantı saat 14:00'te yapılacaktır.")
    assert result["mood_label"] == "neutral"
    assert -0.2 <= result["mood_score"] <= 0.2


def test_detect_mood_empty_fallback() -> None:
    result = mood_detector.detect_mood("")
    assert result["mood_label"] == "neutral"
    assert result["mood_score"] == 0.0


@pytest.mark.anyio
async def test_detect_mood_async() -> None:
    result = await mood_detector.detect_mood_async("Harika bir gün!")
    assert result["mood_label"] == "happy"
    assert result["mood_score"] > 0.0
