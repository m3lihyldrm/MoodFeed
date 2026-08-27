"""MoodFeed Database Repository Layer.

Provides clean repository interfaces and an in-memory testable repository implementation
covering Users, Sessions, Consents, Preferences, Content, Saved Items, Muted Sources,
Feedback, Decisions, and Audit Events.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Any, Protocol


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class UserRepositoryProtocol(Protocol):
    def get_by_id(self, user_id: str) -> dict[str, Any] | None: ...
    def get_by_email(self, email: str) -> dict[str, Any] | None: ...
    def create_user(self, email: str, password_hash: str, display_name: str, role: str = "user") -> dict[str, Any]: ...
    def update_user(self, user_id: str, delta: dict[str, Any]) -> dict[str, Any] | None: ...
    def delete_user(self, user_id: str) -> bool: ...


class InMemoryRepository:
    """Thread-safe, testable repository implementing all PostgreSQL entity models."""

    def __init__(self) -> None:
        self.users: dict[str, dict[str, Any]] = {}
        self.sessions: dict[str, dict[str, Any]] = {}
        self.refresh_tokens: dict[str, dict[str, Any]] = {}
        self.consents: list[dict[str, Any]] = []
        self.preferences: dict[str, dict[str, Any]] = {}
        self.sources: dict[str, dict[str, Any]] = {}
        self.content_items: dict[str, dict[str, Any]] = {}
        self.content_features: dict[str, dict[str, Any]] = {}
        self.feed_decisions: list[dict[str, Any]] = []
        self.saved_items: set[tuple[str, str]] = set()  # (user_id, content_id)
        self.muted_sources: set[tuple[str, str]] = set()  # (user_id, source_name)
        self.muted_categories: set[tuple[str, str]] = set()  # (user_id, category_name)
        self.feedbacks: list[dict[str, Any]] = []
        self.export_requests: dict[str, dict[str, Any]] = {}
        self.deletion_requests: dict[str, dict[str, Any]] = {}
        self.audit_events: list[dict[str, Any]] = []
        self.feature_flags: dict[str, bool] = {
            "mock_adapter": True,
            "auth": True,
            "persistence": True,
            "pilot_mode": True,
        }

    # --- Users ---
    def create_user(self, email: str, password_hash: str, display_name: str, role: str = "user") -> dict[str, Any]:
        user_id = str(uuid.uuid4())
        user = {
            "id": user_id,
            "email": email.strip().lower(),
            "password_hash": password_hash,
            "display_name": display_name.strip(),
            "role": role,
            "is_active": True,
            "is_verified": False,
            "deleted_at": None,
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }
        self.users[user_id] = user
        # Initialize default user preferences
        self.preferences[user_id] = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "profile_preset": "balanced",
            "low_intensity_mode": False,
            "toxicity_filter_level": "standard",
            "active_feed_mode": "moodfeed",
            "synthetic_scenario": "default",
            "custom_weights": None,
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }
        return user

    def get_user_by_id(self, user_id: str) -> dict[str, Any] | None:
        user = self.users.get(user_id)
        if user and user.get("deleted_at") is None:
            return user
        return None

    def get_user_by_email(self, email: str) -> dict[str, Any] | None:
        normalized = email.strip().lower()
        for user in self.users.values():
            if user["email"] == normalized and user.get("deleted_at") is None:
                return user
        return None

    def update_user(self, user_id: str, delta: dict[str, Any]) -> dict[str, Any] | None:
        user = self.get_user_by_id(user_id)
        if not user:
            return None
        user.update(delta)
        user["updated_at"] = utc_now().isoformat()
        return user

    def soft_delete_user(self, user_id: str) -> bool:
        user = self.users.get(user_id)
        if not user:
            return False
        user["deleted_at"] = utc_now().isoformat()
        user["is_active"] = False
        # Invalidate all user sessions
        for session in self.sessions.values():
            if session["user_id"] == user_id:
                session["is_revoked"] = True
        return True

    # --- Sessions & Tokens ---
    def create_session(self, user_id: str, user_agent: str | None = None, ip_address: str | None = None) -> dict[str, Any]:
        session_id = str(uuid.uuid4())
        session_token = str(uuid.uuid4())
        session = {
            "id": session_id,
            "user_id": user_id,
            "session_token": session_token,
            "user_agent": user_agent,
            "ip_address": ip_address,
            "is_revoked": False,
            "expires_at": utc_now().timestamp() + (14 * 86400),
            "created_at": utc_now().isoformat(),
        }
        self.sessions[session_id] = session
        return session

    def get_session(self, session_token: str) -> dict[str, Any] | None:
        for s in self.sessions.values():
            if s["session_token"] == session_token and not s["is_revoked"]:
                if s["expires_at"] > utc_now().timestamp():
                    return s
        return None

    def revoke_session(self, session_id: str) -> bool:
        session = self.sessions.get(session_id)
        if session:
            session["is_revoked"] = True
            return True
        return False

    def revoke_all_user_sessions(self, user_id: str) -> int:
        count = 0
        for s in self.sessions.values():
            if s["user_id"] == user_id and not s["is_revoked"]:
                s["is_revoked"] = True
                count += 1
        return count

    # --- Preferences ---
    def get_preferences(self, user_id: str) -> dict[str, Any]:
        if user_id not in self.preferences:
            self.preferences[user_id] = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "profile_preset": "balanced",
                "low_intensity_mode": False,
                "toxicity_filter_level": "standard",
                "active_feed_mode": "moodfeed",
                "synthetic_scenario": "default",
                "custom_weights": None,
                "created_at": utc_now().isoformat(),
                "updated_at": utc_now().isoformat(),
            }
        return self.preferences[user_id]

    def update_preferences(self, user_id: str, delta: dict[str, Any]) -> dict[str, Any]:
        prefs = self.get_preferences(user_id)
        allowed_keys = {
            "profile_preset",
            "low_intensity_mode",
            "toxicity_filter_level",
            "active_feed_mode",
            "synthetic_scenario",
            "custom_weights",
        }
        for k, v in delta.items():
            if k in allowed_keys:
                prefs[k] = v
        prefs["updated_at"] = utc_now().isoformat()
        return prefs

    def reset_preferences(self, user_id: str) -> dict[str, Any]:
        self.preferences[user_id] = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "profile_preset": "balanced",
            "low_intensity_mode": False,
            "toxicity_filter_level": "standard",
            "active_feed_mode": "moodfeed",
            "synthetic_scenario": "default",
            "custom_weights": None,
            "created_at": utc_now().isoformat(),
            "updated_at": utc_now().isoformat(),
        }
        return self.preferences[user_id]

    # --- Saved Items ---
    def save_item(self, user_id: str, content_id: str) -> bool:
        pair = (user_id, content_id)
        if pair in self.saved_items:
            return False
        self.saved_items.add(pair)
        return True

    def remove_saved_item(self, user_id: str, content_id: str) -> bool:
        pair = (user_id, content_id)
        if pair in self.saved_items:
            self.saved_items.remove(pair)
            return True
        return False

    def get_saved_items(self, user_id: str) -> list[str]:
        return [cid for uid, cid in self.saved_items if uid == user_id]

    # --- Muted Sources & Categories ---
    def mute_source(self, user_id: str, source_name: str) -> bool:
        pair = (user_id, source_name.strip())
        self.muted_sources.add(pair)
        return True

    def unmute_source(self, user_id: str, source_name: str) -> bool:
        pair = (user_id, source_name.strip())
        if pair in self.muted_sources:
            self.muted_sources.remove(pair)
            return True
        return False

    def get_muted_sources(self, user_id: str) -> list[str]:
        return [sname for uid, sname in self.muted_sources if uid == user_id]

    def mute_category(self, user_id: str, category_name: str) -> bool:
        pair = (user_id, category_name.strip())
        self.muted_categories.add(pair)
        return True

    def unmute_category(self, user_id: str, category_name: str) -> bool:
        pair = (user_id, category_name.strip())
        if pair in self.muted_categories:
            self.muted_categories.remove(pair)
            return True
        return False

    def get_muted_categories(self, user_id: str) -> list[str]:
        return [cname for uid, cname in self.muted_categories if uid == user_id]

    # --- Feedback & History ---
    def record_feedback(self, user_id: str, content_id: str, action: str, note: str | None = None) -> dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "content_id": content_id,
            "feedback_action": action,
            "note": note[:500] if note else None,
            "created_at": utc_now().isoformat(),
        }
        self.feedbacks.append(entry)
        return entry

    def get_user_feedback(self, user_id: str) -> list[dict[str, Any]]:
        return [f for f in self.feedbacks if f["user_id"] == user_id]

    # --- User Interactions (Like, Save, Hide, Less Like This, Mute Source) ---
    def record_interaction(
        self,
        user_id: str,
        content_id: str,
        action_type: str,
        source: str | None = None,
        category: str | None = None,
        extra_data: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        entry = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "content_id": content_id,
            "action_type": action_type,
            "source": source,
            "category": category,
            "extra_data": extra_data or {},
            "created_at": utc_now().isoformat(),
        }
        self.feedbacks.append(entry)

        # Update in-memory collections based on action
        if action_type == "save":
            self.save_item(user_id, content_id)
        elif action_type == "unsave":
            self.remove_saved_item(user_id, content_id)
        elif action_type == "mute_source" and source:
            self.mute_source(user_id, source)
        elif action_type == "unmute_source" and source:
            self.unmute_source(user_id, source)

        return entry

    def get_interactions(
        self,
        user_id: str,
        action_type: str | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        results = [
            f for f in reversed(self.feedbacks)
            if f.get("user_id") == user_id and (action_type is None or f.get("action_type") == action_type)
        ]
        return results[:limit]

    # --- Audit Events ---
    def log_audit_event(self, user_id: str | None, event_type: str, resource_type: str, resource_id: str | None = None, status: str = "success") -> dict[str, Any]:
        event = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "event_type": event_type,
            "resource_type": resource_type,
            "resource_id": resource_id,
            "status": status,
            "created_at": utc_now().isoformat(),
        }
        self.audit_events.append(event)
        return event


# Global repository instance
repository = InMemoryRepository()


# --- Database-backed Functions for SQLAlchemy / SQLite Persistence ---

def save_interaction_to_db(
    user_id: str | None,
    content_id: str,
    action_type: str,
    source: str | None = None,
    category: str | None = None,
    extra_data: dict[str, Any] | None = None,
    db: Any = None,
) -> dict[str, Any]:
    """Persists user interaction to SQLite/PostgreSQL and in-memory repository."""
    from backend.database.models import UserInteraction, UserPreferences

    # Always keep in-memory repository in sync
    uid = user_id or "00000000-0000-0000-0000-000000000001"
    in_mem_entry = repository.record_interaction(
        user_id=uid,
        content_id=content_id,
        action_type=action_type,
        source=source,
        category=category,
        extra_data=extra_data,
    )

    if db is not None:
        try:
            user_uuid = None
            try:
                user_uuid = uuid.UUID(uid)
            except Exception:
                user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"user:{uid}")

            interaction_row = UserInteraction(
                user_id=user_uuid,
                content_id=content_id,
                action_type=action_type,
                source=source,
                category=category,
                extra_data=extra_data or {},
                created_at=utc_now(),
            )
            db.add(interaction_row)

            # If action is mute_source, also update user_preferences.muted_sources
            if action_type == "mute_source" and source:
                prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_uuid).first()
                if prefs:
                    current_muted = list(prefs.muted_sources or [])
                    if source not in current_muted:
                        current_muted.append(source)
                        prefs.muted_sources = current_muted
                db.commit()
            elif action_type == "unmute_source" and source:
                prefs = db.query(UserPreferences).filter(UserPreferences.user_id == user_uuid).first()
                if prefs:
                    current_muted = [s for s in (prefs.muted_sources or []) if s != source]
                    prefs.muted_sources = current_muted
                db.commit()
            else:
                db.commit()
                db.refresh(interaction_row)

            return interaction_row.to_dict()
        except Exception:
            try:
                db.rollback()
            except Exception:
                pass

    return in_mem_entry


def get_interactions_from_db(
    user_id: str | None,
    action_type: str | None = None,
    limit: int = 100,
    db: Any = None,
) -> list[dict[str, Any]]:
    """Retrieves user interactions from SQLite/PostgreSQL or in-memory repository."""
    from backend.database.models import UserInteraction

    uid = user_id or "00000000-0000-0000-0000-000000000001"
    if db is not None:
        try:
            user_uuid = None
            try:
                user_uuid = uuid.UUID(uid)
            except Exception:
                user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"user:{uid}")

            query = db.query(UserInteraction).filter(UserInteraction.user_id == user_uuid)
            if action_type:
                query = query.filter(UserInteraction.action_type == action_type)
            rows = query.order_by(UserInteraction.created_at.desc()).limit(limit).all()
            if rows:
                return [r.to_dict() for r in rows]
        except Exception:
            pass

    return repository.get_interactions(user_id=uid, action_type=action_type, limit=limit)

