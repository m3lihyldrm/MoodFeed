from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from backend.main import app
from backend.models import ContentInput, Interaction
from backend.reranking import calculate_spiral_risk, rerank
from backend.scoring import RuleBasedTurkishScorer, ScoreConfig
client = TestClient(app)

def test_health_is_ok() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}

def test_scores_are_bounded_and_toxic_content_scores_higher() -> None:
    scorer = RuleBasedTurkishScorer()
    toxic = scorer.analyze(ContentInput(id="toxic", text="Sen aptalsın, defol."))
    neutral = scorer.analyze(ContentInput(id="neutral", text="Toplantı saat üçte başlayacak."))
    assert all(0 <= value <= 1 for value in [toxic.sentiment.score, toxic.toxicity_score, toxic.negativity_score])
    assert toxic.toxicity_score > neutral.toxicity_score

def test_analyze_endpoint_returns_expected_analysis_fields() -> None:
    response = client.post("/analyze", json={"id": "post-001", "text": "Bugün güzel bir gün", "original_score": 0.5})
    body = response.json()
    assert response.status_code == 200
    assert body["content_id"] == "post-001"
    assert body["sentiment"]["label"] == "positive"

def test_rerank_endpoint_returns_risk_and_ranking_data() -> None:
    response = client.post(
        "/rerank",
        json={"contents": [{"id": "first", "text": "berbat ve stresli", "original_score": 0.8}], "interactions": [{"negativity_score": 0.9}], "enabled": True},
    )
    body = response.json()
    assert response.status_code == 200
    assert body["spiral_risk"]["level"] == "high"
    assert body["contents"][0]["reason"]

def test_high_negative_history_increases_spiral_risk() -> None:
    risk = calculate_spiral_risk([Interaction(negativity_score=0.9) for _ in range(5)])
    assert risk.level == "high" and risk.score >= 0.60 and risk.spiral_detected is True

def test_empty_history_has_low_zero_spiral_risk() -> None:
    risk = calculate_spiral_risk([])
    assert risk.level == "low" and risk.score == 0.0 and risk.spiral_detected is False

def test_disabled_moodfeed_preserves_original_order() -> None:
    contents = [ContentInput(id="first", text="Berbat ve stresli.", original_score=0.9), ContentInput(id="second", text="Güzel ve destekleyici.", original_score=0.1)]
    output, _ = rerank(contents, [], False, RuleBasedTurkishScorer(), ScoreConfig())
    assert [item.content_id for item in output] == ["first", "second"]
    assert [item.new_rank for item in output] == [1, 2]
    assert [item.ranking_score for item in output] == [0.9, 0.1]
    assert "MoodFeed kapalı olduğu için orijinal akış sırası korundu." in output[0].reason

def test_enabled_rerank_returns_reasons_and_transparency() -> None:
    payload = {"contents": [{"id": "a", "text": "Sen aptalsın, defol.", "original_score": 0.9}, {"id": "b", "text": "Umut dolu güzel bir gün.", "original_score": 0.5}], "interactions": [{"negativity_score": 0.9} for _ in range(5)], "enabled": True}
    response = client.post("/rerank", json=payload)
    assert response.status_code == 200 and response.json()["contents"][0]["reason"]
    assert client.get(f"/transparency/{response.json()['contents'][0]['content_id']}").status_code == 200

def test_invalid_request_and_unknown_transparency_return_errors() -> None:
    assert client.post("/analyze", json={"id": "x", "text": ""}).status_code == 422
    assert client.get("/transparency/bilinmeyen").status_code == 404

def test_toggle_changes_feed_mode() -> None:
    toggle_response = client.post("/settings/toggle", json={"enabled": False})
    assert toggle_response.json() == {"enabled": False, "message": "MoodFeed özelliği kapatıldı; orijinal akış sırası korunacaktır."}
    response = client.get("/feed")
    assert response.status_code == 200 and response.json()["moodfeed_enabled"] is False
    client.post("/settings/toggle", json={"enabled": True})

def test_feed_returns_sample_data() -> None:
    response = client.get("/feed")
    assert response.status_code == 200
    assert {item["content_id"] for item in response.json()["contents"]} == {"post-001", "post-002", "post-003", "post-004"}

def test_demo_page_is_available() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "MoodFeed Demo" in response.text

def test_feed_when_disabled_preserves_sample_source_order() -> None:
    client.post("/settings/toggle", json={"enabled": False})
    response = client.get("/feed")
    assert [item["content_id"] for item in response.json()["contents"]] == ["post-001", "post-002", "post-003", "post-004"]
    client.post("/settings/toggle", json={"enabled": True})

def test_rerank_keeps_tied_scores_in_source_order() -> None:
    contents = [ContentInput(id="one", text="nötr", original_score=0.5), ContentInput(id="two", text="nötr", original_score=0.5)]
    output, _ = rerank(contents, [], True, RuleBasedTurkishScorer(), ScoreConfig())
    assert [item.content_id for item in output] == ["one", "two"]

def test_feed_and_rerank_include_scorer_info() -> None:
    with patch("backend.main.scorer", RuleBasedTurkishScorer()):
        response = client.get("/feed")
        assert response.status_code == 200
        body = response.json()
        assert "scorer" in body
        assert body["scorer"]["name"] == "rule_based"
        assert body["scorer"]["label"] == "Kural Tabanlı (Varsayılan ve Kararlı)"
        assert body["scorer"]["mode"] == "rule_based"
        assert body["scorer"]["is_experimental"] is False
        assert body["scorer"]["fallback"] is False
        assert body["scorer"]["fallback_reason"] is None
        assert "transparency_notice" in body

        rerank_res = client.post("/rerank", json={"contents": [{"id": "s-1", "text": "güzel gün", "original_score": 0.5}], "enabled": True})
        assert rerank_res.status_code == 200
        rerank_body = rerank_res.json()
        assert "scorer" in rerank_body
        assert rerank_body["scorer"]["name"] == "rule_based"
        assert rerank_body["scorer"]["is_experimental"] is False
        assert "transparency_notice" in rerank_body


def test_comparison_preserves_content_count_and_ids() -> None:
    response = client.get("/feed")
    assert response.status_code == 200
    body = response.json()
    assert "comparison" in body and body["comparison"] is not None
    comp = body["comparison"]

    orig_ids = [item["content_id"] for item in comp["original"]]
    mood_ids = [item["content_id"] for item in comp["moodfeed"]]

    # 1. Content counts are equal
    assert len(orig_ids) == len(mood_ids) == 4
    # 2. Exact same content IDs present (no deletion, no addition)
    assert set(orig_ids) == set(mood_ids) == {"post-001", "post-002", "post-003", "post-004"}
    # 3. Notice is present
    assert "MoodFeed içerik silmez" in comp["notice"]
    # 4. Each item has ranks and reasons
    for item in comp["moodfeed"]:
        assert item["original_rank"] >= 1
        assert item["new_rank"] >= 1
        assert item["reason"] and len(item["reason"]) > 0


def test_demo_page_contains_ab_comparison_elements() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "A/B Akış Karşılaştırması" in response.text
    assert "MoodFeed içerik silmez; yalnızca kullanıcı kontrollü bir sıralama önerir." in response.text
    assert "original-feed" in response.text
    assert "moodfeed-feed" in response.text
    assert "perf-card" in response.text


def test_performance_metrics_in_feed_and_rerank() -> None:
    with patch("backend.main.scorer", RuleBasedTurkishScorer()):
        response = client.get("/feed")
        assert response.status_code == 200
        body = response.json()
        assert "performance" in body and body["performance"] is not None
        perf = body["performance"]
        assert isinstance(perf["elapsed_ms"], (int, float))
        assert perf["elapsed_ms"] >= 0.0
        assert perf["content_count"] == 4
        assert perf["scorer_mode"] == "rule_based"
        assert perf["measurement"] == "server_side_request_processing"
        assert "X-Process-Time-Ms" in response.headers

        rerank_res = client.post(
            "/rerank",
            json={"contents": [{"id": "p-1", "text": "test metin", "original_score": 0.5}], "enabled": True},
        )
        assert rerank_res.status_code == 200
        rerank_perf = rerank_res.json().get("performance")
        assert rerank_perf is not None
        assert rerank_perf["content_count"] == 1
        assert rerank_perf["scorer_mode"] == "rule_based"
        assert rerank_perf["elapsed_ms"] >= 0.0


def test_performance_metrics_with_berturk_and_fallback() -> None:
    from backend.berturk_scorer import BerturkTurkishScorer

    # 1. BERTurk Active
    mock_pipeline = MagicMock()
    mock_pipeline.return_value = [[
        {"label": "Positive", "score": 0.95},
        {"label": "Notr", "score": 0.03},
        {"label": "Negative", "score": 0.02},
    ]]
    mock_bert = BerturkTurkishScorer(pipeline_instance=mock_pipeline)
    with patch("backend.main.scorer", mock_bert):
        res_bert = client.get("/feed")
        assert res_bert.status_code == 200
        perf_bert = res_bert.json().get("performance")
        assert perf_bert is not None
        assert perf_bert["scorer_mode"] == "berturk"
        assert perf_bert["content_count"] == 4
        assert perf_bert["elapsed_ms"] >= 0.0

    # 2. Fallback
    fb_scorer = BerturkTurkishScorer()
    fb_scorer._tried_loading = True
    fb_scorer._is_loaded = False
    fb_scorer._load_error = "Simulated error"
    with patch("backend.main.scorer", fb_scorer):
        res_fb = client.get("/feed")
        assert res_fb.status_code == 200
        perf_fb = res_fb.json().get("performance")
        assert perf_fb is not None
        assert perf_fb["scorer_mode"] == "rule_based_fallback"
        assert perf_fb["content_count"] == 4
        assert perf_fb["elapsed_ms"] >= 0.0


def test_ranking_reasons_consistency() -> None:
    with patch("backend.main.scorer", RuleBasedTurkishScorer()):
        response = client.get("/feed")
        assert response.status_code == 200
        contents_by_id = {item["content_id"]: item for item in response.json()["contents"]}

        # post-002: negative, original_rank 2 -> new_rank 1 (improved)
        p2 = contents_by_id["post-002"]
        assert p2["original_rank"] == 2 and p2["new_rank"] == 1
        assert any("Çeşitlilik katsayısı" in r for r in p2["reason"])
        assert not any("Akış çeşitliliğini artırmak için içerik öne çıkarıldı" in r for r in p2["reason"])

        # post-001: positive, zero toxicity & negativity, original_rank 1 -> new_rank 2 (dropped)
        p1 = contents_by_id["post-001"]
        assert p1["original_rank"] == 1 and p1["new_rank"] == 2
        assert any("bağıl sıralama puanları" in r for r in p1["reason"])
        assert not any("risk sinyalleri nedeniyle içerik geriye çekildi" in r for r in p1["reason"])

        # post-004: toxic (0.7), original_rank 4 -> new_rank 4 (last position, unchanged)
        p4 = contents_by_id["post-004"]
        assert p4["original_rank"] == 4 and p4["new_rank"] == 4
        assert any("zaten son sırada olduğu için sıra değişmedi" in r for r in p4["reason"])

        # post-003: neutral/positive, unchanged rank 3 -> 3
        p3 = contents_by_id["post-003"]
        assert p3["original_rank"] == 3 and p3["new_rank"] == 3
        assert any("İçerik sırası mevcut sinyallerle korundu" in r for r in p3["reason"])


def test_feed_profile_parameter_and_metadata() -> None:
    # 1. Default (balanced)
    res_def = client.get("/feed")
    assert res_def.status_code == 200
    prof_def = res_def.json().get("profile")
    assert prof_def is not None
    assert prof_def["profile"] == "balanced"
    assert prof_def["profile_label"] == "Dengeli"
    assert prof_def["weights"]["toxicity"] == 0.35

    # 2. Calmer
    res_calm = client.get("/feed?profile=calmer")
    assert res_calm.status_code == 200
    prof_calm = res_calm.json().get("profile")
    assert prof_calm is not None
    assert prof_calm["profile"] == "calmer"
    assert prof_calm["profile_label"] == "Daha Sakin Akış"
    assert prof_calm["weights"]["toxicity"] == 0.50

    # 3. User Control
    res_usr = client.get("/feed?profile=user_control")
    assert res_usr.status_code == 200
    prof_usr = res_usr.json().get("profile")
    assert prof_usr is not None
    assert prof_usr["profile"] == "user_control"
    assert prof_usr["profile_label"] == "Kullanıcı Kontrolü"
    assert prof_usr["weights"]["toxicity"] == 0.15


def test_profile_weights_affect_scores_and_ranking() -> None:
    res_calm = client.get("/feed?profile=calmer")
    res_usr = client.get("/feed?profile=user_control")

    calm_contents = {item["content_id"]: item for item in res_calm.json()["contents"]}
    usr_contents = {item["content_id"]: item for item in res_usr.json()["contents"]}

    # Content counts are preserved
    assert len(calm_contents) == len(usr_contents) == 4

    # Toxic post-004 should have lower score under calmer (penalty 0.50 * 0.7 = 0.35 -> 0.43) than user_control (penalty 0.15 * 0.7 = 0.105 -> 0.675)
    score_calm = calm_contents["post-004"]["ranking_score"]
    score_usr = usr_contents["post-004"]["ranking_score"]
    assert score_calm < score_usr


def test_demo_page_contains_control_center_elements() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Akış Kontrol Merkezi" in response.text
    assert "Daha Sakin Akış" in response.text
    assert "Kullanıcı Kontrolü" in response.text
    assert "Silinen İçerik: 0" in response.text
    assert "Sıralamayı Geri Al" in response.text


def test_mathematical_reproducibility_of_profile_scores() -> None:
    for prof in ["balanced", "calmer", "user_control"]:
        res = client.get(f"/feed?profile={prof}")
        assert res.status_code == 200
        data = res.json()
        scores = [item["ranking_score"] for item in data["contents"]]
        assert scores == sorted(scores, reverse=True)


def test_feed_scenario_default_preserves_behavior() -> None:
    res = client.get("/feed?scenario=default")
    assert res.status_code == 200
    data = res.json()
    assert data["spiral_risk"]["score"] == 0.0
    assert data["spiral_risk"]["level"] == "low"
    assert data["spiral_risk"]["spiral_detected"] is False
    assert data["scenario"]["name"] == "default"
    assert data["scenario"]["synthetic"] is False
    assert data["scenario"]["notice"] is None


def test_feed_scenario_high_negativity() -> None:
    res = client.get("/feed?scenario=high_negativity")
    assert res.status_code == 200
    data = res.json()
    assert data["spiral_risk"]["score"] >= 0.60
    assert data["spiral_risk"]["level"] == "high"
    assert data["spiral_risk"]["spiral_detected"] is True
    assert data["scenario"]["name"] == "high_negativity"
    assert data["scenario"]["synthetic"] is True
    assert "jüri demosu" in data["scenario"]["notice"]

    contents_by_id = {item["content_id"]: item for item in data["contents"]}
    assert len(contents_by_id) == 4

    # With high risk, positive post-001 gets diversity bonus (0.15 * 1.0 * risk) -> ~0.78
    # negative post-002 gets negativity penalty -> ~0.66
    # So post-001 ranks #1 and post-002 ranks below it
    assert contents_by_id["post-001"]["new_rank"] < contents_by_id["post-002"]["new_rank"]


def test_feed_invalid_scenario_returns_422() -> None:
    res = client.get("/feed?scenario=unsupported_scenario")
    assert res.status_code == 422


def test_demo_page_contains_scenario_toggle() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "Simüle Edilmiş Olumsuzluk Sinyali" in response.text
    assert "Sentetik senaryo" in response.text


def test_demo_page_contains_spiral_warning_card() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert "spiral-warning-card" in response.text
    assert "Bu özelliği kapat" in response.text
    assert "Olumsuzluk Sarmalı Riski Algılandı" in response.text


def test_high_negativity_toxic_score_decreases_and_does_not_get_diversity_bonus() -> None:
    res_def = client.get("/feed?scenario=default")
    res_high = client.get("/feed?scenario=high_negativity")

    def_items = {item["content_id"]: item for item in res_def.json()["contents"]}
    high_items = {item["content_id"]: item for item in res_high.json()["contents"]}

    # Toxic post-004 must NOT increase score under high negativity scenario
    score_def = def_items["post-004"]["ranking_score"]
    score_high = high_items["post-004"]["ranking_score"]
    assert score_high < score_def

    # Toxic item must not get balancing reason
    assert not any("dengeleyici içerik öne çıkarıldı" in r for r in high_items["post-004"]["reason"])


def test_neutral_content_promotion_reason() -> None:
    # When a neutral item with high score improves rank, its reason should mention initial score, not positive emotion
    body = {
        "contents": [
            {"id": "c-1", "text": "Hava bugün 20 derece.", "original_score": 0.3},
            {"id": "c-2", "text": "Yeni özellik yayınlandı.", "original_score": 0.9},
        ],
        "enabled": True,
    }
    res = client.post("/rerank", json=body)
    assert res.status_code == 200
    c2 = next(item for item in res.json()["contents"] if item["content_id"] == "c-2")
    assert c2["new_rank"] == 1
    assert any("Başlangıç sıralama puanı" in r for r in c2["reason"])
    assert not any("Olumlu duygu" in r for r in c2["reason"])


def test_contextual_toxicity_mention_reason() -> None:
    # A sentence mentioning toxic themes without being directly abusive
    content = {"id": "c-meta", "text": "Saldırgan ve hakaret içeren mesajlar görmek istemiyorum."}
    res = client.post("/analyze", json=content)
    assert res.status_code == 200
    data = res.json()
    assert data["toxicity_score"] == 0.0
    assert any("Metin saldırgan içerikten söz ediyor; ancak doğrudan bir kişiye saldırı içermiyor." in r for r in data["reason"])


def test_score_breakdown_presence_and_reproducibility() -> None:
    res = client.get("/feed?profile=balanced")
    assert res.status_code == 200
    data = res.json()
    for item in data["contents"]:
        assert "score_breakdown" in item
        bd = item["score_breakdown"]
        assert bd is not None
        assert "original_score" in bd
        assert "toxicity_penalty" in bd
        assert "negativity_penalty" in bd
        assert "diversity_bonus" in bd
        assert "final_score" in bd
        expected = max(0.0, min(1.0, round(bd["original_score"] - bd["toxicity_penalty"] - bd["negativity_penalty"] + bd["diversity_bonus"], 3)))
        assert abs(bd["final_score"] - expected) <= 0.001
        assert abs(item["ranking_score"] - bd["final_score"]) <= 0.001


def test_demo_page_contains_drawer_and_reset_elements() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "drawer" in html
    assert "Kararı İncele" in html
    assert "Demo'yu Sıfırla" in html
    assert "Matematiksel Skor Formülü" in html
    assert "Escape" in html


def test_demo_page_contains_guided_tour_decision_trace_and_telemetry() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "start-tour-btn" in html
    assert "tour-banner" in html
    assert "Demo Rehberini Başlat" in html
    assert "Decision Trace" in html or "Dikey Karar İzi" in html
    assert "Oturum Telemetrisi" in html
    assert 'role="dialog"' in html
    assert 'aria-modal="true"' in html


def test_demo_page_contains_moodfeed_experience_screens() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "screen-welcome" in html
    assert "screen-scenario" in html
    assert "screen-profile" in html
    assert "screen-analyzing" in html
    assert "screen-results" in html
    assert "navigateTo" in html
    assert "hashchange" in html
    assert "prefers-reduced-motion" in html


def test_demo_page_contains_pilot_evaluation_elements() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "start-pilot-btn" in html
    assert "screen-pilot-consent" in html
    assert "pilot-consent-agree-btn" in html
    assert "pilot-consent-decline-btn" in html
    assert "screen-pilot-survey" in html
    assert "survey-error-alert" in html
    assert 'role="alert"' in html
    assert "field-understandability" in html
    assert "screen-pilot-results" in html
    assert "pilot-tasks-widget" in html
    assert "Henüz tamamlanmış pilot değerlendirme verisi yok." in html
    assert "İçerik Sinyali Maruziyeti" in html


def test_demo_page_contains_pilot_export_elements() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "export-pilot-json-btn" in html
    assert "export-pilot-csv-btn" in html
    assert "exportPilotJSON" in html
    assert "exportPilotCSV" in html
    assert "Dışa aktarma için pilot anketini tamamlayın." in html
    assert "exploratory_prototype_feedback" in html


def test_demo_page_contains_task_quality_metrics() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "Görev Kalitesi ve Süre Analizi" in html
    assert "task-quality-table" in html
    assert "task-quality-tbody" in html
    assert "task_quality_metrics" in html
    assert "error_count" in html or "errorCount" in html
    assert "retry_count" in html or "retryCount" in html
    assert "duration_ms" in html or "durationMs" in html


def test_demo_page_contains_mvp_app_screens_and_navigation() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    # Check 12 standard screens
    assert "screen-welcome" in html
    assert "screen-onboarding" in html
    assert "screen-feed" in html
    assert "screen-content" in html
    assert "screen-insights" in html
    assert "screen-compare" in html
    assert "screen-preferences" in html
    assert "screen-settings" in html
    assert "screen-help" in html
    assert "screen-pilot-consent" in html
    assert "screen-pilot-survey" in html
    assert "screen-pilot-results" in html
    assert "screen-not-found" in html

    # Check Sidebar and Mobile Navigation
    assert "app-sidebar" in html
    assert "mobile-bottom-nav" in html
    assert "nav-feed" in html
    assert "nav-insights" in html
    assert "nav-compare" in html
    assert "nav-preferences" in html


def test_demo_page_contains_search_filter_sort_and_detail() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    # Search, Filter, Sort
    assert "feed-search-input" in html
    assert "feed-search-clear" in html
    assert "feed-sort-select" in html
    assert "tab-all" in html
    assert "tab-saved" in html
    assert "tab-recent" in html
    assert "tab-low_density" in html
    assert "tab-explained" in html

    # Content Detail and Drawer
    assert "screen-content" in html
    assert "detail-author" in html
    assert "detail-sentiment" in html
    assert "detail-save-btn" in html
    assert "detail-revert-btn" in html
    assert "drawer" in html
    assert "drawer-overlay" in html


def test_demo_page_contains_accessibility_and_privacy_elements() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    # Privacy, Zero Storage & Reset Modal
    assert "reset-confirm-modal" in html
    assert "confirmResetDemo" in html
    assert "localStorage" not in html or "localStorage.clear" not in html
    assert "Sıfır Kalıcı Depolama" in html or "RAM Bellek" in html
    assert "prefers-reduced-motion" in html
    assert 'aria-live="assertive"' in html or 'aria-live="polite"' in html


def test_production_contracts_and_mock_adapter_present() -> None:
    res = client.get("/")
    assert res.status_code == 200
    html = res.text
    assert "auth-boundary-modal" in html
    assert "auth-status-btn" in html
    assert "MoodFeedApiAdapter" in html
    assert "simulateAuthLogin" in html

    from pathlib import Path
    assert Path("docs/contracts/domain_models.ts").exists()
    assert Path("docs/contracts/api_specification.md").exists()
    assert Path("docs/production_architecture.md").exists()
