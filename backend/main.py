import json
import logging
import os
import time
from pathlib import Path
from typing import Literal
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

# Load environment variables early
ROOT_DIR = Path(__file__).resolve().parent.parent
env_file = ROOT_DIR / ".env"
if env_file.exists():
    load_dotenv(dotenv_path=env_file, override=False)
else:
    load_dotenv(override=False)

from backend.api.preferences import router as preferences_router
from backend.api.v1_router import router as v1_router
from backend.api.explainer import router as explainer_router
from backend.api.auth import router as auth_router
from backend.api.posts import router as posts_router
from backend.api.activity import router as activity_router
from backend.api.interactions import router as interactions_router
from backend.api.admin import router as admin_router
from backend.api.webhooks import router as webhooks_router
from backend.api.analytics import router as analytics_router
from backend.config import settings as app_settings
from backend.db.database import init_db
from backend.models import (
    AnalysisResult,
    ContentInput,
    FeedComparison,
    Interaction,
    PerformanceMetrics,
    ProfileMetadata,
    RankedContent,
    RerankRequest,
    RerankResponse,
    ScenarioMetadata,
    ToggleRequest,
    ToggleResponse,
)
from backend.reranking import rerank
from backend.scoring import PROFILE_CONFIGS, SCENARIO_CONFIGS, ScoreConfig, get_scorer

logger = logging.getLogger("moodfeed.main")
logging.basicConfig(level=getattr(logging, app_settings.log_level, logging.INFO))

FEED_PATH = ROOT_DIR / "data" / "sample_feed.json"
DEMO_PATH = ROOT_DIR / "frontend" / "index.html"
scorer, config = get_scorer(), ScoreConfig()
feed_settings = {"enabled": True}
last_results: dict[str, RankedContent] = {}

app = FastAPI(
    title="MoodFeed MVP",
    version=app_settings.app_version,
    description="Türkçe odaklı, açıklanabilir içerik akışı prototipi.",
)


@app.on_event("startup")
def startup_event():
    try:
        init_db()
    except Exception as e:
        logger.warning("Database initialization warning: %s", e)

    is_clerk = bool(
        app_settings.auth_provider == "clerk"
        and app_settings.feature_flag_clerk_auth
        and app_settings.clerk_publishable_key
    )
    clerk_pub_masked = (
        (app_settings.clerk_publishable_key[:12] + "..." + app_settings.clerk_publishable_key[-4:])
        if app_settings.clerk_publishable_key
        else "NOT_CONFIGURED"
    )
    secret_status = "CONFIGURED" if app_settings.clerk_secret_key else "NOT_SET"
    mock_status = "ENABLED" if app_settings.feature_flag_mock_adapter else "DISABLED (Pure Clerk Mode)"

    banner = f"""
================================================================================
 MoodFeed Backend v{app_settings.app_version} ({app_settings.app_env.upper()})
--------------------------------------------------------------------------------
 [Auth Provider]       : {"CLERK AUTH" if is_clerk else "LOCAL JWT (Mock Auth)"}
 [Clerk Publishable]   : {clerk_pub_masked}
 [Clerk Secret Key]    : {secret_status}
 [Clerk Issuer]        : {app_settings.clerk_issuer or 'Auto-derived'}
 [Clerk JWKS URL]      : {app_settings.clerk_jwks_url or 'Auto-derived'}
 [Mock Auth Adapter]   : {mock_status}
 [Database URL]        : {app_settings.database_url}
 [ML Scorer Mode]      : {app_settings.model_provider}
 [Base URL]            : {app_settings.app_base_url}
================================================================================
"""
    print(banner)
    logger.info("[Startup] MoodFeed backend ready. Active auth provider: %s", "clerk" if is_clerk else "local")

app.include_router(preferences_router)
app.include_router(auth_router)
app.include_router(posts_router)
app.include_router(activity_router)
app.include_router(interactions_router)
app.include_router(admin_router)
app.include_router(webhooks_router)
app.include_router(analytics_router)
app.include_router(v1_router)
app.include_router(explainer_router)
app.add_middleware(
    CORSMiddleware,
    allow_origins=app_settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_process_time_header(request, call_next):
    req_start = time.perf_counter()
    response = await call_next(request)
    http_process_time_ms = (time.perf_counter() - req_start) * 1000.0
    response.headers["X-Process-Time-Ms"] = f"{http_process_time_ms:.2f}"
    return response

def load_sample_feed() -> list[ContentInput]:
    """Yerel örnek veriyi okur; veriler gerçek kişisel veri içermez."""
    try:
        return [ContentInput(**item) for item in json.loads(FEED_PATH.read_text(encoding="utf-8"))]
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Örnek akış verisi okunamadı.") from error

def load_live_feed() -> list[ContentInput]:
    """Canlı Türkçe haber RSS servisinden içerikleri çeker; hata veya erişilememe durumunda yerel örnek veriye fallback yapar."""
    try:
        from backend.services.rss_service import rss_service
        items = rss_service.get_live_content_inputs(limit=30)
        if items and len(items) > 0:
            return items
    except Exception as e:
        logger.warning("[Feed] Canlı RSS servisi çağrılırken hata oluştu, yerel akışa dönülüyor: %s", e)
    return load_sample_feed()

def load_feed_contents(source: str | None = None) -> list[ContentInput]:
    """İstenen kaynağa göre (canlı RSS veya deterministik örnek veri) içerikleri yükler."""
    feed_mode = (source or os.getenv("MOODFEED_FEED_SOURCE", "")).strip().lower()
    if feed_mode == "sample":
        return load_sample_feed()
    if feed_mode in ("live", "rss") or not os.getenv("PYTEST_CURRENT_TEST"):
        return load_live_feed()
    return load_sample_feed()

def build_response(request: RerankRequest, user_id: str | None = None) -> RerankResponse:
    start_time = time.perf_counter()
    selected_profile = request.profile if request.profile in PROFILE_CONFIGS else "balanced"
    profile_config, profile_meta = PROFILE_CONFIGS[selected_profile]

    selected_scenario = request.scenario if request.scenario in SCENARIO_CONFIGS else "default"
    scenario_meta = SCENARIO_CONFIGS[selected_scenario]

    interactions = request.interactions
    if selected_scenario in ("high_negativity", "highNegativity") and not interactions:
        interactions = [Interaction(negativity_score=0.85), Interaction(negativity_score=0.85)]
    elif selected_scenario in ("high_toxicity", "highToxicity") and not interactions:
        interactions = [Interaction(negativity_score=0.90), Interaction(negativity_score=0.90)]
    elif selected_scenario in ("balanced_calmer", "balancedCalmer") and not interactions:
        interactions = [Interaction(negativity_score=0.20)]

    muted_sources: list[str] = []
    less_liked_ids: list[str] = []
    hidden_ids: list[str] = []

    if user_id:
        try:
            from backend.database.repository import get_interactions_from_db
            user_actions = get_interactions_from_db(user_id=user_id, limit=200)
            for act in user_actions:
                atype = act.get("action_type")
                cid = act.get("content_id")
                src = act.get("source")
                if atype == "mute_source" and src:
                    muted_sources.append(src)
                elif atype == "less_like_this" and cid:
                    less_liked_ids.append(cid)
                elif atype == "hide" and cid:
                    hidden_ids.append(cid)
        except Exception as e:
            logger.debug("Failed to load user interactions: %s", e)

    contents, risk = rerank(
        request.contents,
        interactions,
        request.enabled,
        scorer,
        profile_config,
        muted_sources=muted_sources,
        less_liked_ids=less_liked_ids,
        hidden_ids=hidden_ids,
    )
    elapsed_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    global last_results
    last_results = {item.content_id: item for item in contents}
    scorer_info = getattr(scorer, "get_info", lambda: None)()
    if scorer_info is None or scorer_info.name == "rule_based":
        warning = "Bu MVP klinik tanı koymaz; sonuçlar kural tabanlı tahminlerdir."
    elif scorer_info.fallback:
        warning = f"Bu MVP klinik tanı koymaz; BERTurk yüklenemediği için kural tabanlı fallback devrededir ({scorer_info.fallback_reason or 'bilinmeyen hata'})."
    else:
        warning = "Bu MVP klinik tanı koymaz; sonuçlar makine öğrenmesi destekli tahminlerdir."

    original_list = sorted(contents, key=lambda c: c.original_rank)
    changed_count = sum(1 for c in contents if c.new_rank != c.original_rank)
    comparison_data = FeedComparison(
        original=original_list,
        moodfeed=contents,
        changed_count=changed_count,
        notice="MoodFeed içerik silmez; yalnızca sıralama önerir.",
    )

    scorer_mode = scorer_info.mode if scorer_info else "rule_based"
    performance_data = PerformanceMetrics(
        elapsed_ms=elapsed_ms,
        content_count=len(contents),
        scorer_mode=scorer_mode,
        measurement="server_side_request_processing",
    )

    return RerankResponse(
        moodfeed_enabled=request.enabled,
        spiral_risk=risk,
        contents=contents,
        scorer=scorer_info,
        warning=warning,
        transparency_notice="Model tahminleri kesin gerçeklik değildir; akış sıralaması deneysel/prototip bir sinyaldir.",
        comparison=comparison_data,
        performance=performance_data,
        profile=profile_meta,
        scenario=scenario_meta,
    )

@app.get("/", include_in_schema=False)
def demo_page() -> FileResponse:
    """Bağımlılıksız yerel demo arayüzünü sunar."""
    return FileResponse(DEMO_PATH)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/feed", response_model=RerankResponse)
def get_feed(
    profile: Literal["balanced", "calmer", "user_control"] = "balanced",
    scenario: Literal["default", "high_negativity", "highNegativity", "high_toxicity", "highToxicity", "balanced_calmer", "balancedCalmer"] = "default",
    source: Literal["live", "rss", "sample"] | None = None,
    user_id: str | None = None,
) -> RerankResponse:
    return build_response(
        RerankRequest(
            contents=load_feed_contents(source=source),
            interactions=[],
            enabled=feed_settings["enabled"],
            profile=profile,
            scenario=scenario,
        ),
        user_id=user_id,
    )

@app.post("/analyze", response_model=AnalysisResult)
def analyze(content: ContentInput) -> AnalysisResult:
    return scorer.analyze(content)

@app.post("/rerank", response_model=RerankResponse)
def rerank_feed(request: RerankRequest) -> RerankResponse:
    return build_response(request)

@app.post("/settings/toggle", response_model=ToggleResponse)
def toggle_settings(request: ToggleRequest) -> ToggleResponse:
    feed_settings["enabled"] = request.enabled
    return ToggleResponse(
        enabled=request.enabled,
        message="MoodFeed özelliği açıldı."
        if request.enabled
        else "MoodFeed özelliği kapatıldı; orijinal akış sırası korunacaktır.",
    )

@app.get("/transparency/{content_id}")
def transparency(content_id: str) -> dict[str, object]:
    item = last_results.get(content_id)
    if item is None:
        raise HTTPException(status_code=404, detail="İçerik bulunamadı. Önce /feed veya /rerank çağrısı yapın.")
    return {
        "content_id": content_id,
        "original_rank": item.original_rank,
        "new_rank": item.new_rank,
        "reason": item.reason,
        "scorer": item.scorer,
        "notice": "Sıralama gerekçesi kural tabanlı MVP mantığıyla üretilmiştir.",
        "transparency_notice": "Model tahminleri kesin gerçeklik değildir; akış sıralaması deneysel/prototip bir sinyaldir.",
    }
