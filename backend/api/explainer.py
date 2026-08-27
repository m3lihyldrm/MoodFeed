"""MoodFeed LLM Complementary Explainer API Endpoint.

Implements POST /v1/explain taking content, scores, and context to return
a natural language AI explanation for algorithmic transparency.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter
from pydantic import BaseModel, Field
from backend.services.llm_explainer import explain_decision

router = APIRouter(prefix="/v1")


class ExplainRequest(BaseModel):
    content: dict[str, Any] | Any = Field(default_factory=dict)
    scores: dict[str, Any] | None = Field(default=None)
    context: dict[str, Any] | None = Field(default=None)


class ExplainResponse(BaseModel):
    explanation: str
    source: str = "llm_explainer"
    confidence: float = 0.95


@router.post("/explain", response_model=ExplainResponse)
def explain_decision_endpoint(request: ExplainRequest) -> ExplainResponse:
    """Generates a natural language explanation for an algorithmic ranking decision."""
    text = explain_decision(request.content, request.scores, request.context)
    return ExplainResponse(explanation=text, source="llm_explainer", confidence=0.95)
