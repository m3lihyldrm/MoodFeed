"""User Preferences Service re-exports for backward compatibility."""

from __future__ import annotations

import uuid
from typing import Any
from sqlalchemy.orm import Session
from backend.services.preferences_service import (
    _normalize_uuid,
    get_or_create_user,
    get_preferences,
    save_preferences,
)


def update_preferences(
    db: Session,
    user_id: uuid.UUID | str,
    active_profile: str | None = None,
    active_scenario: str | None = None,
    muted_sources: list[str] | list[Any] | None = None,
    **kwargs: Any,
):
    """Updates user preferences and returns the updated record."""
    delta: dict[str, Any] = {**kwargs}
    if active_profile is not None:
        delta["active_profile"] = active_profile
    if active_scenario is not None:
        delta["active_scenario"] = active_scenario
    if muted_sources is not None:
        delta["muted_sources"] = muted_sources
    return save_preferences(user_id=user_id, preferences=delta, db=db)
