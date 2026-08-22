import json
import time
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .api.v1_router import router as v1_router
from .models import AnalysisResult, ContentInput, FeedComparison, Interaction, PerformanceMetrics, ProfileMetadata, RankedContent, RerankRequest, RerankResponse, ScenarioMetadata, ToggleRequest, ToggleResponse
from .reranking import rerank
from .scoring import PROFILE_CONFIGS, ScoreConfig, get_scorer

ROOT_DIR = Path(__file__).resolve().parent.parent
FEED_PATH = ROOT_DIR / "data" / "sample_feed.json"
DEMO_PATH = ROOT_DIR / "frontend" / "index.html"
scorer, config = get_scorer(), ScoreConfig()
settings = {"enabled": True}
last_results: dict[str, RankedContent] = {}

SCENARIO_CONFIGS: dict[str, ScenarioMetadata] = {
    "default": ScenarioMetadata(
        name="default",
        label="Varsayılan Demo",
        synthetic=False,
        notice=None,
    ),
    "high_negativity": ScenarioMetadata(
        name="high_negativity",
        label="Simüle Edilmiş Yüksek Olumsuzluk",
        synthetic=True,
        notice="Bu senaryo yalnızca jüri demosu için oluşturulmuştur; gerçek kullanıcı ruh hâlini veya klinik bir durumu temsil etmez.",
    ),
}

app = FastAPI(title="MoodFeed MVP", version="0.1.0", description="Türkçe odaklı, açıklanabilir içerik akışı prototipi.")
app.include_router(v1_router)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

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

def build_response(request: RerankRequest) -> RerankResponse:
    start_time = time.perf_counter()
    selected_profile = request.profile if request.profile in PROFILE_CONFIGS else "balanced"
    profile_config, profile_meta = PROFILE_CONFIGS[selected_profile]

    selected_scenario = request.scenario if request.scenario in SCENARIO_CONFIGS else "default"
    scenario_meta = SCENARIO_CONFIGS[selected_scenario]

    interactions = request.interactions
    if selected_scenario == "high_negativity" and not interactions:
        interactions = [Interaction(negativity_score=0.85), Interaction(negativity_score=0.85)]

    contents, risk = rerank(request.contents, interactions, request.enabled, scorer, profile_config)
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
    scenario: Literal["default", "high_negativity"] = "default",
) -> RerankResponse:
    return build_response(RerankRequest(
        contents=load_sample_feed(),
        interactions=[],
        enabled=settings["enabled"],
        profile=profile,
        scenario=scenario,
    ))

@app.post("/analyze", response_model=AnalysisResult)
def analyze(content: ContentInput) -> AnalysisResult:
    return scorer.analyze(content)

@app.post("/rerank", response_model=RerankResponse)
def rerank_feed(request: RerankRequest) -> RerankResponse:
    return build_response(request)

@app.post("/settings/toggle", response_model=ToggleResponse)
def toggle_settings(request: ToggleRequest) -> ToggleResponse:
    settings["enabled"] = request.enabled
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
