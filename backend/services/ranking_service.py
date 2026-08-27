"""MoodFeed Ranking Service.

Pure, deterministic, versioned ranking engine calculating score breakdowns
and producing stable feed orderings based on explicit user profile weights.
"""

from __future__ import annotations

from typing import Any
from backend.models import ContentInput, RankedContent, ScoreBreakdown
from backend.reranking import calculate_spiral_risk, rerank
from backend.scoring import ContentScorer, ScoreConfig, get_scorer


class RankingService:
    """Production Ranking Engine Service (Version 1.2.0)."""

    VERSION: str = "1.2.0"

    def __init__(self, scorer: ContentScorer | None = None) -> None:
        self.scorer = scorer or get_scorer()

    def rank_feed(
        self,
        contents: list[ContentInput],
        profile_config: ScoreConfig,
        interactions: list[Any] | None = None,
        enabled: bool = True,
    ) -> tuple[list[RankedContent], Any]:
        """Calculates deterministic ranking scores and stable output ordering."""
        return rerank(
            contents=contents,
            interactions=interactions or [],
            enabled=enabled,
            scorer=self.scorer,
            config=profile_config,
        )


# Global ranking service
ranking_service = RankingService()
