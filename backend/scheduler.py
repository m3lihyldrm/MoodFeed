"""MoodFeed AsyncIOScheduler Configuration.

Provides background job scheduling for periodic RSS news ingestion.
"""

from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

try:
    from backend.services.rss_service import rss_service
    from backend.config import settings
except ImportError:
    from services.rss_service import rss_service
    from config import settings

logger = logging.getLogger("moodfeed.scheduler")

scheduler = AsyncIOScheduler()

interval_mins = getattr(settings, "rss_sync_interval_minutes", 1) or 1
scheduler.add_job(
    rss_service.ingest_all,
    trigger=IntervalTrigger(minutes=interval_mins),
    id="rss_ingestion",
    replace_existing=True,
)


def start_scheduler() -> None:
    """Starts the background scheduler if enabled by configuration and not already running."""
    if not getattr(settings, "rss_scheduler_enabled", True):
        logger.info("[Scheduler] AsyncIOScheduler start skipped: RSS_SCHEDULER_ENABLED is false.")
        return

    if not scheduler.running:
        try:
            scheduler.start()
            logger.info("[Scheduler] AsyncIOScheduler started successfully (Interval: %d min).", interval_mins)
        except Exception as e:
            logger.warning("[Scheduler] Error starting scheduler: %s", e)


def shutdown_scheduler() -> None:
    """Gracefully shuts down the background scheduler."""
    if scheduler.running:
        try:
            scheduler.shutdown(wait=False)
            logger.info("[Scheduler] AsyncIOScheduler shutdown.")
        except Exception as e:
            logger.warning("[Scheduler] Error shutting down scheduler: %s", e)
