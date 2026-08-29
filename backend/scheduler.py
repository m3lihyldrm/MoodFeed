"""MoodFeed AsyncIOScheduler Configuration.

Provides background job scheduling for periodic RSS news ingestion (every 1 minute).
"""

from __future__ import annotations

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger

try:
    from backend.services.rss_service import rss_service
except ImportError:
    from services.rss_service import rss_service

logger = logging.getLogger("moodfeed.scheduler")

scheduler = AsyncIOScheduler()

# Her 1 dakikada bir RSS ingestion
scheduler.add_job(
    rss_service.ingest_all,
    trigger=IntervalTrigger(minutes=1),
    id="rss_ingestion",
    replace_existing=True,
)


def start_scheduler() -> None:
    """Starts the background scheduler if not already running."""
    if not scheduler.running:
        try:
            scheduler.start()
            logger.info("[Scheduler] AsyncIOScheduler started successfully (Interval: 1 min).")
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
