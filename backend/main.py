import json
from pathlib import Path
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from .models import AnalysisResult, ContentInput, RankedContent, RerankRequest, RerankResponse, ToggleRequest, ToggleResponse
from .reranking import rerank
from .scoring import RuleBasedTurkishScorer, ScoreConfig

ROOT_DIR = Path(__file__).resolve().parent.parent
FEED_PATH = ROOT_DIR / "data" / "sample_feed.json"
DEMO_PATH = ROOT_DIR / "frontend" / "index.html"
scorer, config = RuleBasedTurkishScorer(), ScoreConfig()
settings = {"enabled": True}
last_results: dict[str, RankedContent] = {}

app = FastAPI(title="MoodFeed MVP", version="0.1.0", description="Türkçe odaklı, açıklanabilir içerik akışı prototipi.")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

def load_sample_feed() -> list[ContentInput]:
    """Yerel örnek veriyi okur; veriler gerçek kişisel veri içermez."""
    try:
        return [ContentInput(**item) for item in json.loads(FEED_PATH.read_text(encoding="utf-8"))]
    except (OSError, json.JSONDecodeError, ValueError) as error:
        raise HTTPException(status_code=500, detail="Örnek akış verisi okunamadı.") from error

def build_response(request: RerankRequest) -> RerankResponse:
    contents, risk = rerank(request.contents, request.interactions, request.enabled, scorer, config)
    global last_results
    last_results = {item.content_id: item for item in contents}
    return RerankResponse(moodfeed_enabled=request.enabled, spiral_risk=risk, contents=contents, warning="Bu MVP klinik tanı koymaz; sonuçlar kural tabanlı tahminlerdir.")

@app.get("/", include_in_schema=False)
def demo_page() -> FileResponse:
    """Bağımlılıksız yerel demo arayüzünü sunar."""
    return FileResponse(DEMO_PATH)

@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}

@app.get("/feed", response_model=RerankResponse)
def get_feed() -> RerankResponse:
    return build_response(RerankRequest(contents=load_sample_feed(), interactions=[], enabled=settings["enabled"]))

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
    return {"content_id": content_id, "original_rank": item.original_rank, "new_rank": item.new_rank, "reason": item.reason, "notice": "Sıralama gerekçesi kural tabanlı MVP mantığıyla üretilmiştir."}
