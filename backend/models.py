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

class AnalysisResult(BaseModel):
    content_id: str
    text: str
    sentiment: Sentiment
    toxicity_score: float = Field(ge=0, le=1)
    negativity_score: float = Field(ge=0, le=1)
    reason: list[str]

class RankedContent(AnalysisResult):
    original_rank: int = Field(ge=1)
    new_rank: int = Field(ge=1)
    ranking_score: float = Field(ge=0, le=1)

class RiskResult(BaseModel):
    score: float = Field(ge=0, le=1)
    level: Literal["low", "medium", "high"]

class RerankRequest(BaseModel):
    contents: list[ContentInput] = Field(min_length=1, max_length=100)
    interactions: list[Interaction] = Field(default_factory=list, max_length=100)
    enabled: bool = True

class RerankResponse(BaseModel):
    moodfeed_enabled: bool
    spiral_risk: RiskResult
    contents: list[RankedContent]
    warning: str

class ToggleRequest(BaseModel):
    enabled: bool

class ToggleResponse(BaseModel):
    enabled: bool
    message: str
