import sys
from typing import Any, Literal
from pydantic import AliasChoices, BaseModel, Field

if __name__ == "backend.models":
    sys.modules.setdefault("models", sys.modules["backend.models"])
elif __name__ == "models":
    sys.modules.setdefault("backend.models", sys.modules["models"])

class ContentInput(BaseModel):
    """Skorlanacak sosyal medya veya haber içeriği."""
    model_config = {"populate_by_name": True, "extra": "ignore"}

    id: str = Field(min_length=1, validation_alias=AliasChoices("id", "content_id"))
    text: str = Field(min_length=1, max_length=5_000)
    original_score: float = Field(default=0.5, ge=0, le=1)
    title: str | None = None
    url: str | None = Field(default=None, validation_alias=AliasChoices("url", "link"))
    source: str | None = None
    author: str | None = None
    category: str | None = None
    published_at: str | None = None
    image_url: str | None = None
    user_metadata: dict[str, Any] | None = None

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

class MetaSignals(BaseModel):
    account_age_days: int = 365
    posts_per_hour: float = 1.0
    repetition_ratio: float = 0.1
    spam_score: float = 0.0
    bot_risk: Literal["low", "medium", "high"] = "low"

class AnalysisResult(BaseModel):
    model_config = {"populate_by_name": True, "extra": "ignore"}

    content_id: str
    text: str
    sentiment: Sentiment
    toxicity_score: float = Field(ge=0, le=1)
    negativity_score: float = Field(ge=0, le=1)
    spam_score: float = Field(default=0.0, ge=0, le=1)
    bot_risk: Literal["low", "medium", "high"] = "low"
    meta_signals: dict[str, Any] | None = None
    reason: list[str]
    scorer: ScorerInfo | None = None
    title: str | None = None
    url: str | None = Field(default=None, validation_alias=AliasChoices("url", "link"))
    source: str | None = None
    author: str | None = None
    category: str | None = None
    published_at: str | None = None
    image_url: str | None = None

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
    spiral_detected: bool = False
    average_score: float | None = None

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
    name: Literal["default", "high_negativity", "highNegativity", "high_toxicity", "highToxicity", "balanced_calmer", "balancedCalmer"]
    label: str
    synthetic: bool
    notice: str | None = None

class RerankRequest(BaseModel):
    contents: list[ContentInput] = Field(min_length=1, max_length=100)
    interactions: list[Interaction] = Field(default_factory=list, max_length=100)
    enabled: bool = True
    profile: Literal["balanced", "calmer", "user_control"] = "balanced"
    scenario: Literal["default", "high_negativity", "highNegativity", "high_toxicity", "highToxicity", "balanced_calmer", "balancedCalmer"] = "default"

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

class UserActionCreate(BaseModel):
    user_id: str | None = None
    content_id: str = Field(min_length=1)
    action_type: Literal["like", "save", "hide", "less_like_this", "mute_source", "unlike", "unsave", "unmute_source"]
    source: str | None = None
    category: str | None = None
    extra_data: dict[str, Any] | None = None

class UserActionRead(BaseModel):
    id: str
    user_id: str | None = None
    content_id: str
    action_type: str
    source: str | None = None
    category: str | None = None
    created_at: str | None = None

class UserActionResponse(BaseModel):
    success: bool
    message: str
    action: UserActionRead | None = None

UserActionCreate.model_rebuild()
UserActionRead.model_rebuild()
UserActionResponse.model_rebuild()

# Re-export SQLAlchemy database entity models for unified imports
try:
    from backend.database.models import (
        Base,
        User,
        Post,
        Like,
        Save,
        Comment,
        Follow,
        Notification,
        UserPreferences,
        UserInteraction,
        InteractionLog,
    )
except ImportError:
    pass



