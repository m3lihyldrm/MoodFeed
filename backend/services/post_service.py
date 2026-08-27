"""MoodFeed Post & Interaction Service.

Manages persistent database operations for posts, likes, saves, and profiles.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any
from sqlalchemy.orm import Session
from backend.database.models import Like, Post, Save, User
from backend.db.database import get_db, _get_fallback_sessionmaker


def _normalize_uuid(val: uuid.UUID | str) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class PersistentPostService:
    """Encapsulates Post CRUD operations."""

    def create_post(
        self,
        user_id: uuid.UUID | str,
        content: str,
        title: str | None = None,
        category: str = "Gündem",
        author: str | None = None,
        handle: str | None = None,
        sentiment_label: str = "neutral",
        sentiment_score: float = 0.5,
        negativity_score: float = 0.1,
        toxicity_score: float = 0.0,
        db: Session | None = None,
    ) -> dict[str, Any]:
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            uid = _normalize_uuid(user_id)
            post_id = uuid.uuid4()
            post = Post(
                id=post_id,
                user_id=uid,
                content=content,
                title=title or content[:40] + ("..." if len(content) > 40 else ""),
                author=author or "Kullanıcı",
                handle=handle or "@kullanici",
                category=category,
                sentiment_label=sentiment_label,
                sentiment_score=sentiment_score,
                negativity_score=negativity_score,
                toxicity_score=toxicity_score,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
            session.add(post)
            session.commit()
            session.refresh(post)
            return post.to_dict()
        except Exception:
            session.rollback()
            raise
        finally:
            if not session_provided:
                session.close()

    def get_posts(self, limit: int = 50, offset: int = 0, db: Session | None = None) -> list[dict[str, Any]]:
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            posts = session.query(Post).order_by(Post.created_at.desc()).offset(offset).limit(limit).all()
            return [p.to_dict() for p in posts]
        finally:
            if not session_provided:
                session.close()

    def get_post_by_id(self, post_id: uuid.UUID | str, db: Session | None = None) -> dict[str, Any] | None:
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            pid = _normalize_uuid(post_id)
            post = session.query(Post).filter(Post.id == pid).first()
            return post.to_dict() if post else None
        finally:
            if not session_provided:
                session.close()


# Singleton post service instance
post_service = PersistentPostService()
