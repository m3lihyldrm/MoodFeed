"""MoodFeed Live Activity, Notifications, and Online Community API Router."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Header, Query
from backend.services.activity_service import activity_service

router = APIRouter(tags=["activity"])


@router.get("/v1/activity")
@router.get("/activity")
def get_live_activity(limit: int = Query(8, ge=1, le=50)) -> dict[str, Any]:
    """Canlı aktivite akışını döner."""
    return activity_service.get_activity(limit=limit)


@router.get("/v1/online")
@router.get("/online")
def get_online_status() -> dict[str, Any]:
    """Çevrimiçi kullanıcılar ve aktif tartışma sayılarını döner."""
    return activity_service.get_online_users()


@router.get("/v1/notifications")
@router.get("/notifications")
def get_user_notifications(authorization: str | None = Header(None)) -> dict[str, Any]:
    """Kullanıcı bildirimlerini döner."""
    return activity_service.get_notifications()
