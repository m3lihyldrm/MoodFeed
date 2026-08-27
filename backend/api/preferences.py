"""User Preferences API Router for MoodFeed.

Provides REST endpoints for fetching and updating user preferences via PostgreSQL / SQLAlchemy:
- GET /v1/preferences: Fetches user preferences
- PUT /v1/preferences: Updates user preferences
"""

from __future__ import annotations

import time
import uuid
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.auth.service import auth_service
from backend.db.database import get_db
from backend.services.preferences_service import get_preferences as svc_get_preferences
from backend.services.preferences_service import save_preferences as svc_save_preferences

router = APIRouter(prefix="/v1/preferences", tags=["preferences"])


def _resolve_user_id(
    authorization: str | None = Header(None),
    user_id: str | None = Query(None, description="Kullanıcı UUID"),
) -> str:
    """Resolves user_id from Bearer token or query parameter; raises 401 if unauthenticated."""
    if user_id:
        return user_id
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1]
        user = auth_service.get_current_user_from_token(token)
        if user:
            return user["id"]
    raise HTTPException(
        status_code=401,
        detail={
            "code": "UNAUTHORIZED",
            "message": "Bu işlem için geçerli bir oturum gereklidir.",
            "request_id": f"req-{int(time.time()*1000)}",
            "field_errors": {},
            "retryable": False,
        },
    )


class PreferencesUpdate(BaseModel):
    spiral_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    negative_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    positive_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    toxicity_threshold: float | None = Field(default=None, ge=0.0, le=1.0)
    theme: str | None = Field(default=None)
    active_profile: str | None = None
    active_scenario: str | None = None
    profile_preset: str | None = None
    low_intensity_mode: bool | None = None
    toxicity_filter_level: str | None = None
    active_feed_mode: str | None = None
    synthetic_scenario: str | None = None
    muted_sources: list[str] | None = None


class PreferencesResponse(BaseModel):
    user_id: str
    spiral_threshold: float = 0.7
    negative_threshold: float = 0.6
    positive_threshold: float = 0.5
    toxicity_threshold: float = 0.6
    theme: str = "light"
    active_profile: str = "balanced"
    active_scenario: str = "default"
    profile_preset: str = "balanced"
    low_intensity_mode: bool = False
    muted_sources: list[str] = Field(default_factory=list)
    updated_at: str | None = None


@router.get("", response_model=PreferencesResponse)
@router.get("/", response_model=PreferencesResponse, include_in_schema=False)
def get_preferences(
    authorization: str | None = Header(None),
    user_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Kullanıcı tercihlerini PostgreSQL'den döner."""
    uid = _resolve_user_id(authorization=authorization, user_id=user_id)
    prefs = svc_get_preferences(user_id=uid, db=db)
    return prefs.to_dict()


@router.put("", response_model=PreferencesResponse)
@router.put("/", response_model=PreferencesResponse, include_in_schema=False)
@router.patch("", response_model=PreferencesResponse, include_in_schema=False)
def update_preferences(
    payload: PreferencesUpdate,
    authorization: str | None = Header(None),
    user_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Kullanıcı tercihlerini PostgreSQL'de günceller."""
    uid = _resolve_user_id(authorization=authorization, user_id=user_id)
    delta = payload.model_dump(exclude_unset=True)
    prefs = svc_save_preferences(user_id=uid, preferences=delta, db=db)
    return prefs.to_dict()


# Additional compatibility endpoints
@router.get("/me", response_model=PreferencesResponse)
def get_user_preferences_me(
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    prefs = svc_get_preferences(user_id=user_id, db=db)
    return prefs.to_dict()


@router.post("/me", response_model=PreferencesResponse)
def update_user_preferences_me(
    payload: PreferencesUpdate,
    user_id: str = Query(default="00000000-0000-0000-0000-000000000001"),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    delta = payload.model_dump(exclude_unset=True)
    prefs = svc_save_preferences(user_id=user_id, preferences=delta, db=db)
    return prefs.to_dict()


@router.post("/reset", response_model=PreferencesResponse)
def reset_user_preferences(
    authorization: str | None = Header(None),
    user_id: str | None = Query(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    uid = _resolve_user_id(authorization=authorization, user_id=user_id)
    default_prefs = {
        "spiral_threshold": 0.7,
        "negative_threshold": 0.6,
        "positive_threshold": 0.5,
        "toxicity_threshold": 0.6,
        "theme": "light",
        "active_profile": "balanced",
        "active_scenario": "default",
        "profile_preset": "balanced",
        "muted_sources": [],
    }
    prefs = svc_save_preferences(user_id=uid, preferences=default_prefs, db=db)
    return prefs.to_dict()
