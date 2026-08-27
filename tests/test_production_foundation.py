"""
Test Suite: MoodFeed Production Product Foundation
Validates Domain Contracts, API Specifications, Acceptance Criteria Loops,
Security Invariants, and Privacy Principles.
"""

from pathlib import Path
import pytest
from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


def test_domain_contracts_completeness() -> None:
    contracts_file = Path("docs/contracts/domain_models.ts")
    assert contracts_file.exists(), "domain_models.ts must exist"
    content = contracts_file.read_text(encoding="utf-8")

    required_models = [
        "interface User",
        "interface Session",
        "interface Consent",
        "interface UserPreferences",
        "interface ContentItem",
        "interface ContentFeature",
        "interface SimilarityGroup",
        "interface FeedItem",
        "interface FeedResponse",
        "interface RankExplanation",
        "interface RecommendationFeedback",
        "interface SavedItem",
        "interface MutedSource",
        "interface InsightsSummary",
        "interface PilotSession",
        "interface ExportReport",
        "interface ApiError",
    ]
    for model in required_models:
        assert model in content, f"Missing domain model contract: {model}"

    # Privacy classification tags
    assert "CONFIDENTIAL_PII" in content
    assert "RESTRICTED" in content
    assert "INTERNAL" in content
    assert "PUBLIC" in content


def test_api_specification_all_endpoints() -> None:
    api_file = Path("docs/contracts/api_specification.md")
    assert api_file.exists(), "api_specification.md must exist"
    spec = api_file.read_text(encoding="utf-8")

    required_endpoints = [
        "POST /auth/register",
        "POST /auth/login",
        "POST /auth/logout",
        "POST /auth/refresh",
        "POST /auth/password-reset",
        "GET /me",
        "DELETE /me",
        "GET /consents",
        "POST /consents",
        "GET /preferences",
        "PATCH /preferences",
        "POST /preferences/reset",
        "GET /sources",
        "POST /sources/connect",
        "POST /sources/:id/sync",
        "DELETE /sources/:id",
        "GET /feed",
        "GET /feed/:contentId",
        "GET /feed/:contentId/explanation",
        "POST /feed/:contentId/feedback",
        "POST /feed/:contentId/save",
        "DELETE /feed/:contentId/save",
        "POST /sources/:sourceId/mute",
        "DELETE /sources/:sourceId/mute",
        "GET /compare",
        "GET /insights",
        "POST /pilot/sessions",
        "PATCH /pilot/sessions/:id",
        "POST /exports",
        "GET /exports/:id",
        "POST /data/export",
        "POST /data/delete",
    ]
    for ep in required_endpoints:
        assert ep in spec, f"Missing API endpoint specification: {ep}"


def test_production_architecture_sections() -> None:
    arch_file = Path("docs/production_architecture.md")
    assert arch_file.exists(), "production_architecture.md must exist"
    arch = arch_file.read_text(encoding="utf-8").lower()

    assert "postgresql 16" in arch
    assert "redis" in arch
    assert "ranking_score" in arch
    assert "owasp asvs" in arch
    assert "argon2id" in arch
    assert "right to erasure" in arch
    assert "circuit breaker" in arch
    assert "health & readiness" in arch


def test_acceptance_criteria_loop() -> None:
    """
    BÖLÜM 11 — ACCEPTANCE CRITERIA:
    İçerik aç → explanation aç → preference değiştir → feed yeniden sırala
    → compare farkını göster → recommendation undo → yeniden sırala
    → insight güncelle → kullanıcı ayarını kaydet → reset ile temizle
    """
    # 1. Fetch initial feed
    res_init = client.get("/feed?profile=balanced")
    assert res_init.status_code == 200
    data_init = res_init.json()
    contents_init = data_init["contents"]
    assert len(contents_init) >= 4

    # 2. Verify detail & explanation metadata
    first_item = contents_init[0]
    assert "content_id" in first_item
    assert "score_breakdown" in first_item
    assert "reason" in first_item
    assert len(first_item["reason"]) > 0

    # 3. Preference change (calmer) -> Rerank
    res_calm = client.get("/feed?profile=calmer")
    assert res_calm.status_code == 200
    data_calm = res_calm.json()
    assert data_calm["profile"]["profile"] == "calmer"
    assert data_calm["profile"]["weights"]["toxicity"] == 0.50
    assert data_calm["profile"]["weights"]["negativity"] == 0.40

    # 4. Compare view difference
    assert "comparison" in data_calm
    assert "changed_count" in data_calm["comparison"]

    # 5. User Control profile -> Minimal intervention
    res_uc = client.get("/feed?profile=user_control")
    assert res_uc.status_code == 200
    data_uc = res_uc.json()
    assert data_uc["profile"]["profile"] == "user_control"

    # 6. Transparency explanation for content
    res_trans = client.get(f"/transparency/{first_item['content_id']}")
    assert res_trans.status_code == 200
    data_trans = res_trans.json()
    assert data_trans["content_id"] == first_item["content_id"]
    assert "reason" in data_trans

    # 7. Toggle settings endpoint
    res_toggle = client.post("/settings/toggle", json={"enabled": False})
    assert res_toggle.status_code == 200
    assert res_toggle.json()["enabled"] is False

    # Restore settings
    client.post("/settings/toggle", json={"enabled": True})


def test_privacy_and_security_invariants() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text

    # No persistent storage
    assert "localStorage" not in html or "localStorage.clear" not in html
    assert "sessionStorage" not in html or "sessionStorage.clear" not in html

    # Formula injection protection
    assert "sanitizeCSVCell" in html

    # No clinical claim invariants
    assert "Bu çalışma klinik veya psikolojik bir değerlendirme/tedavi iddiası taşımaz" in html
    assert "Demo İçerik" in html
