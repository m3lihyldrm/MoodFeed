"""Unit and Integration Tests for Jury Critical Fixes.

Verifies:
1. ToxicityAnalyzer meta-signals (account_age_days, posts_per_hour, repetition_ratio, keyword_stuffing)
2. 'Hangi Verileri Kullandık?' button, modal and transparency panel
3. Pseudonymized KVKK compliant storage text in Settings & Privacy
4. Rule-based explanation UI integration and toxicity badge data attributes
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import ContentInput
from backend.scoring import RuleBasedTurkishScorer
from backend.services.toxicity_service import ToxicityAnalyzer, toxicity_analyzer

client = TestClient(app)


def test_toxicity_analyzer_meta_signals_young_account() -> None:
    """Account age < 7 days adds 0.3 to spam score."""
    analyzer = ToxicityAnalyzer()
    res = analyzer.analyze("Harika bir teknoloji haberi", user_metadata={"account_age_days": 3})
    assert res["spam_score"] >= 0.3
    assert res["meta_signals"]["account_age_days"] == 3


def test_toxicity_analyzer_meta_signals_high_frequency() -> None:
    """Posts per hour > 10 adds 0.4 to spam score."""
    analyzer = ToxicityAnalyzer()
    res = analyzer.analyze("Normal bir içerik metni", user_metadata={"posts_per_hour": 15})
    assert res["spam_score"] >= 0.4
    assert res["meta_signals"]["posts_per_hour"] == 15


def test_toxicity_analyzer_meta_signals_high_repetition() -> None:
    """Repetition ratio > 0.5 adds 0.3 to spam score."""
    analyzer = ToxicityAnalyzer()
    res = analyzer.analyze("Normal içerik", user_metadata={"repetition_ratio": 0.75})
    assert res["spam_score"] >= 0.3
    assert res["meta_signals"]["repetition_ratio"] == 0.75


def test_toxicity_analyzer_combined_bot_risk_high() -> None:
    """Combined meta signals trigger high bot risk when spam score > 0.5."""
    analyzer = ToxicityAnalyzer()
    # Young account (0.3) + high post rate (0.4) = 0.7 (> 0.5 -> high bot risk)
    res = analyzer.analyze(
        "Saldırgan aptal mesaj",
        user_metadata={"account_age_days": 2, "posts_per_hour": 20, "repetition_ratio": 0.6},
    )
    assert res["toxicity_score"] > 0
    assert res["spam_score"] > 0.5
    assert res["bot_risk"] == "high"


def test_rule_based_scorer_integrates_meta_signals() -> None:
    """RuleBasedTurkishScorer populates spam_score, bot_risk, meta_signals in AnalysisResult."""
    scorer = RuleBasedTurkishScorer()
    content = ContentInput(
        id="test-post-1",
        text="Sen ne aptal adamsın defol git",
        user_metadata={"account_age_days": 2, "posts_per_hour": 15},
    )
    result = scorer.analyze(content)
    assert result.toxicity_score > 0
    assert result.spam_score >= 0.5
    assert result.bot_risk == "high"
    assert result.meta_signals is not None
    assert any("spam/bot riski" in r.lower() for r in result.reason)


def test_frontend_contains_data_sources_button_and_modal() -> None:
    """UI contains 'Hangi Verileri Kullandık?' panel, button and modal."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "transparency-panel" in html
    assert "Hangi Verileri Kullandık?" in html
    assert "showDataSources" in html
    assert "data-sources-modal" in html
    assert "14 RSS Haber Kaynağı" in html
    assert "Kelime Sözlüğü" in html
    assert "Meta Sinyaller" in html
    assert "closeDataSources" in html


def test_frontend_contains_corrected_kvkk_storage_text() -> None:
    """UI contains KVKK compliant pseudonymized storage text instead of zero storage claim."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "Takma adlı, KVKK'ya uygun depolama" in html
    assert "Kişisel veriler şifrelenmiş (PostgreSQL)" in html
    assert "Kimlik gizli (takma adlı user_id)" in html
    assert "İstediğiniz zaman silebilirsiniz (GDPR)" in html
    assert "3. taraflara veri satılmıyor" in html


def test_frontend_contains_rule_based_explanation_and_toxicity_badges() -> None:
    """UI displays Rule-based explanation badge and toxicity badge with data attributes."""
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    assert "Kural Tabanlı Açıklama" in html
    assert "toxicity-badge" in html
    assert "data-toxicity" in html
    assert "data-spam" in html
    assert "drawer-meta-signals-card" in html
    assert "showRuleExplanation" in html
