from typing import Literal
from pydantic import AliasChoices, BaseModel, Field

class ContentInput(BaseModel):
    """Skorlanacak sosyal medya içeriği."""
    model_config = {"populate_by_name": True}

    id: str = Field(min_length=1, validation_alias=AliasChoices("id", "content_id"))
    text: str = Field(min_length=1, max_length=2_000)
    original_score: float = Field(default=0.5, ge=0, le=1)

class Interaction(BaseModel):
    """Kimlik içermeyen istemci etkileşim özeti."""
    negativity_score: float = Field(ge=0, le=1)

class Sentiment(BaseModel):
    label: Literal["positive", "neutral", "negative"]
    score: float = Field(ge=0, le=1)

class ScorerInfo(BaseModel):
    name: Literal["rule_based", "berturk", "rule_based_fallback"]
    label: str
    model_name: str | None = None
    fallback: bool = False
    fallback_reason: str | None = None
    mode: Literal["rule_based", "berturk", "rule_based_fallback"] = "rule_based"
    is_experimental: bool = False
    loaded: bool = True

class AnalysisResult(BaseModel):
    content_id: str
    text: str
    sentiment: Sentiment
    toxicity_score: float = Field(ge=0, le=1)
    negativity_score: float = Field(ge=0, le=1)
    reason: list[str]
    scorer: ScorerInfo | None = None

class ScoreBreakdown(BaseModel):
    original_score: float = Field(ge=0, le=1)
    toxicity_penalty: float = Field(ge=0)
    negativity_penalty: float = Field(ge=0)
    diversity_bonus: float = Field(ge=0)
    final_score: float = Field(ge=0, le=1)

class RankedContent(AnalysisResult):
    original_rank: int = Field(ge=1)
    new_rank: int = Field(ge=1)
    ranking_score: float = Field(ge=0, le=1)
    score_breakdown: ScoreBreakdown | None = None

class RiskResult(BaseModel):
    score: float = Field(ge=0, le=1)
    level: Literal["low", "medium", "high"]

class ProfileWeights(BaseModel):
    toxicity: float
    negativity: float
    diversity: float

class ProfileMetadata(BaseModel):
    profile: Literal["balanced", "calmer", "user_control"]
    profile_label: str
    weights: ProfileWeights
    description: str

class ScenarioMetadata(BaseModel):
    name: Literal["default", "high_negativity"]
    label: str
    synthetic: bool
    notice: str | None = None

class RerankRequest(BaseModel):
    contents: list[ContentInput] = Field(min_length=1, max_length=100)
    interactions: list[Interaction] = Field(default_factory=list, max_length=100)
    enabled: bool = True
    profile: Literal["balanced", "calmer", "user_control"] = "balanced"
    scenario: Literal["default", "high_negativity"] = "default"

class FeedComparison(BaseModel):
    original: list[RankedContent]
    moodfeed: list[RankedContent]
    changed_count: int
    notice: str = "MoodFeed içerik silmez; yalnızca sıralama önerir."

class PerformanceMetrics(BaseModel):
    elapsed_ms: float = Field(ge=0.0)
    content_count: int = Field(ge=0)
    scorer_mode: Literal["rule_based", "berturk", "rule_based_fallback"]
    measurement: str = "server_side_request_processing"

class RerankResponse(BaseModel):
    moodfeed_enabled: bool
    spiral_risk: RiskResult
    contents: list[RankedContent]
    warning: str
    scorer: ScorerInfo | None = None
    transparency_notice: str = "Model tahminleri kesin gerçeklik değildir; akış sıralaması deneysel/prototip bir sinyaldir."
    comparison: FeedComparison | None = None
    performance: PerformanceMetrics | None = None
    profile: ProfileMetadata | None = None
    scenario: ScenarioMetadata | None = None

class ToggleRequest(BaseModel):
    enabled: bool

class ToggleResponse(BaseModel):
    enabled: bool
    message: str
