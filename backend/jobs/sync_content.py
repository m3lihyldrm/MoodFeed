"""MoodFeed Scheduled Content Synchronization Job.

Fetches latest news from configured RSS feeds, performs AI signal scoring
(sentiment, negativity, toxicity), and saves normalized posts into the database.
"""

from __future__ import annotations

import logging
from typing import Any
from backend.ingestion.rss_feed import rss_parser, DEFAULT_RSS_FEED_URL
from backend.scoring import ContentInput, MoodScorer
from backend.services.post_service import post_service
from backend.services.auth_service import auth_service

logger = logging.getLogger("moodfeed.jobs.sync_content")


class ContentSyncJob:
    """Synchronizes external RSS feeds into MoodFeed post database."""

    def __init__(self, scorer: MoodScorer | None = None) -> None:
        self.scorer = scorer or MoodScorer()

    def sync_feed(
        self,
        feed_url: str = DEFAULT_RSS_FEED_URL,
        limit: int = 15,
    ) -> dict[str, Any]:
        """Fetches, scores, and stores new posts from the RSS feed."""
        raw_items = rss_parser.fetch_feed(feed_url)
        if not raw_items:
            logger.info("No items fetched from RSS feed %s", feed_url)
            return {"synced_count": 0, "items": []}

        # Ensure a default system user for RSS news posts
        system_user = auth_service.get_user_by_email("rss.bot@moodfeed.app")
        if not system_user:
            try:
                system_user = auth_service.register(
                    email="rss.bot@moodfeed.app",
                    password="RssBotSecurePass2026!",
                    username="haber_botu",
                    display_name="Haber Kaynağı",
                )
            except Exception:
                # Fallback to demo user
                system_user = auth_service.get_user_by_email("demo.kullanici@moodfeed.app")

        user_id = "00000000-0000-0000-0000-000000000001"
        if isinstance(system_user, dict):
            user_id = system_user.get("id") or system_user.get("user", {}).get("id") or user_id
        elif hasattr(system_user, "id"):
            user_id = str(system_user.id)
        synced_posts: list[dict[str, Any]] = []

        for item in raw_items[:limit]:
            text_content = item.get("text") or item.get("title") or ""
            if not text_content:
                continue

            # Score content with MoodScorer
            content_input = ContentInput(
                id=item.get("guid", "rss-item"),
                text=text_content,
                source=item.get("author", "Haber Kaynağı"),
                category=item.get("category", "Gündem"),
            )
            analysis = self.scorer.analyze(content_input)

            created_post = post_service.create_post(
                user_id=user_id,
                content=text_content,
                title=item.get("title"),
                category=item.get("category", "Gündem"),
                author=item.get("author", "Haber Kaynağı"),
                handle="@" + item.get("author", "haber").lower().replace(" ", ""),
                sentiment_label=analysis.sentiment.label,
                sentiment_score=analysis.sentiment.score,
                negativity_score=analysis.negativity_score,
                toxicity_score=analysis.toxicity_score,
            )
            synced_posts.append(created_post)

        logger.info("Successfully synced %d items from RSS feed", len(synced_posts))
        return {
            "synced_count": len(synced_posts),
            "feed_url": feed_url,
            "posts": synced_posts,
        }


# Singleton job runner
content_sync_job = ContentSyncJob()


def run_sync() -> dict[str, Any]:
    """Entry point for periodic scheduler / background worker."""
    return content_sync_job.sync_feed()


if __name__ == "__main__":
    result = run_sync()
    print(f"Content sync completed: {result['synced_count']} items.")
