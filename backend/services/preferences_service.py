"""User Preferences Service for PostgreSQL persistence.

Manages fetching, creating, and updating UserPreferences in PostgreSQL / SQLite.
"""

from __future__ import annotations

import contextlib
import datetime
import uuid
from typing import Any, Generator
from sqlalchemy.orm import Session
from backend.database.models import User, UserPreferences
from backend.db.database import SessionLocal, _get_fallback_sessionmaker


def _normalize_uuid(user_id: uuid.UUID | str) -> uuid.UUID:
    """Normalizes string or UUID instance to uuid.UUID."""
    if isinstance(user_id, uuid.UUID):
        return user_id
    try:
        return uuid.UUID(str(user_id))
    except (ValueError, TypeError, AttributeError):
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(user_id))


@contextlib.contextmanager
def _session_scope(db: Session | None = None) -> Generator[Session, None, None]:
    """Provides a transactional scope around a series of database operations."""
    if db is not None:
        yield db
        return

    try:
        session = SessionLocal()
        session.connection()
    except Exception:
        sm = _get_fallback_sessionmaker()
        session = sm()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_or_create_user(db: Session, user_id: uuid.UUID | str) -> User:
    """Ensures user exists in the database, creating the user record if absent."""
    uid = _normalize_uuid(user_id)
    now = datetime.datetime.now(datetime.timezone.utc)
    user = db.query(User).filter(User.id == uid).first()
    if user is None:
        user = User(id=uid, created_at=now, last_seen_at=now)
        db.add(user)
        db.flush()
    else:
        user.last_seen_at = now
    return user


def get_preferences(user_id: uuid.UUID | str, db: Session | None = None) -> UserPreferences:
    """Retrieves user preferences from PostgreSQL; creates default preferences if absent.

    Parameters:
        user_id: User UUID or string
        db: Optional SQLAlchemy Session (opens a managed session if omitted)

    Returns:
        UserPreferences entity instance
    """
    uid = _normalize_uuid(user_id)
    now = datetime.datetime.now(datetime.timezone.utc)

    with _session_scope(db) as session:
        get_or_create_user(session, uid)
        prefs = session.query(UserPreferences).filter(UserPreferences.user_id == uid).first()
        if prefs is None:
            prefs = UserPreferences(
                user_id=uid,
                spiral_threshold=0.7,
                negative_threshold=0.6,
                positive_threshold=0.5,
                toxicity_threshold=0.6,
                theme="light",
                active_profile="balanced",
                active_scenario="default",
                profile_preset="balanced",
                muted_sources=[],
                updated_at=now,
            )
            session.add(prefs)
            session.commit()
            session.refresh(prefs)
        return prefs


def save_preferences(
    user_id: uuid.UUID | str,
    preferences: dict[str, Any] | UserPreferences | Any,
    db: Session | None = None,
) -> UserPreferences:
    """Saves/updates user preferences in PostgreSQL and returns the updated entity.

    Parameters:
        user_id: User UUID or string
        preferences: Dictionary or object containing preference key-values
        db: Optional SQLAlchemy Session (opens a managed session if omitted)

    Returns:
        Updated UserPreferences entity instance
    """
    uid = _normalize_uuid(user_id)
    now = datetime.datetime.now(datetime.timezone.utc)

    pref_dict: dict[str, Any] = {}
    if isinstance(preferences, dict):
        pref_dict = preferences
    elif hasattr(preferences, "model_dump"):
        pref_dict = preferences.model_dump(exclude_unset=True)
    elif hasattr(preferences, "to_dict"):
        pref_dict = preferences.to_dict()
    elif hasattr(preferences, "__dict__"):
        pref_dict = {k: v for k, v in preferences.__dict__.items() if not k.startswith("_")}

    with _session_scope(db) as session:
        get_or_create_user(session, uid)
        prefs = session.query(UserPreferences).filter(UserPreferences.user_id == uid).first()
        if prefs is None:
            prefs = UserPreferences(
                user_id=uid,
                spiral_threshold=float(pref_dict.get("spiral_threshold", 0.7)),
                negative_threshold=float(pref_dict.get("negative_threshold", 0.6)),
                positive_threshold=float(pref_dict.get("positive_threshold", 0.5)),
                toxicity_threshold=float(pref_dict.get("toxicity_threshold", 0.6)),
                theme=str(pref_dict.get("theme", "light")),
                active_profile=str(pref_dict.get("active_profile", "balanced")),
                active_scenario=str(pref_dict.get("active_scenario", "default")),
                profile_preset=str(pref_dict.get("profile_preset", pref_dict.get("active_profile", "balanced"))),
                muted_sources=list(pref_dict.get("muted_sources", [])),
                updated_at=now,
            )
            session.add(prefs)
        else:
            if "spiral_threshold" in pref_dict and pref_dict["spiral_threshold"] is not None:
                prefs.spiral_threshold = float(pref_dict["spiral_threshold"])
            if "negative_threshold" in pref_dict and pref_dict["negative_threshold"] is not None:
                prefs.negative_threshold = float(pref_dict["negative_threshold"])
            if "positive_threshold" in pref_dict and pref_dict["positive_threshold"] is not None:
                prefs.positive_threshold = float(pref_dict["positive_threshold"])
            if "toxicity_threshold" in pref_dict and pref_dict["toxicity_threshold"] is not None:
                prefs.toxicity_threshold = float(pref_dict["toxicity_threshold"])
            if "theme" in pref_dict and pref_dict["theme"] is not None:
                prefs.theme = str(pref_dict["theme"])
            if "active_profile" in pref_dict and pref_dict["active_profile"] is not None:
                prefs.active_profile = str(pref_dict["active_profile"])
                prefs.profile_preset = str(pref_dict["active_profile"])
            if "active_scenario" in pref_dict and pref_dict["active_scenario"] is not None:
                prefs.active_scenario = str(pref_dict["active_scenario"])
            if "profile_preset" in pref_dict and pref_dict["profile_preset"] is not None:
                prefs.profile_preset = str(pref_dict["profile_preset"])
                prefs.active_profile = str(pref_dict["profile_preset"])
            if "low_intensity_mode" in pref_dict and pref_dict["low_intensity_mode"] is not None:
                prefs.low_intensity_mode = bool(pref_dict["low_intensity_mode"])
            if "muted_sources" in pref_dict and pref_dict["muted_sources"] is not None:
                prefs.muted_sources = list(pref_dict["muted_sources"])
            prefs.updated_at = now

        session.commit()
        session.refresh(prefs)
        return prefs
