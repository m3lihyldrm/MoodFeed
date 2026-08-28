"""MoodFeed Notification Service.

Provides notification creation, retrieval, read receipts, and lifecycle management
for likes, comments, follows, and mentions.
"""

from __future__ import annotations

import datetime
import logging
import uuid
from typing import Any
from sqlalchemy.orm import Session
from backend.database.models import Notification, User
from backend.db.database import _get_fallback_sessionmaker

logger = logging.getLogger("moodfeed.services.notifications")


def _normalize_uuid(val: uuid.UUID | str) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class NotificationService:
    """Production Notification management service backed by PostgreSQL/SQLite."""

    def create_notification(
        self,
        user_id: str | uuid.UUID,
        actor_user_id: str | uuid.UUID | None,
        type: str,
        post_id: str | uuid.UUID | None = None,
        comment_id: str | uuid.UUID | None = None,
        db: Session | None = None,
    ) -> dict[str, Any] | None:
        """Creates a new notification if actor is not the recipient."""
        uid = _normalize_uuid(user_id)
        actor_uid = _normalize_uuid(actor_user_id) if actor_user_id else None

        # Do not notify user about their own actions
        if actor_uid and uid == actor_uid:
            return None

        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            pid = _normalize_uuid(post_id) if post_id else None
            cid = _normalize_uuid(comment_id) if comment_id else None

            notif = Notification(
                id=uuid.uuid4(),
                user_id=uid,
                actor_user_id=actor_uid,
                type=type,
                post_id=pid,
                comment_id=cid,
                is_read=False,
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
            session.add(notif)
            if not session_provided:
                session.commit()
                session.refresh(notif)
            else:
                session.flush()

            return notif.to_dict()
        except Exception as e:
            if not session_provided:
                session.rollback()
            logger.error(f"Failed to create notification: {e}")
            return None
        finally:
            if not session_provided:
                session.close()

    def get_user_notifications(
        self,
        user_id: str | uuid.UUID,
        limit: int = 50,
        unread_only: bool = False,
        db: Session | None = None,
    ) -> list[dict[str, Any]]:
        """Retrieves user notifications ordered by newest first."""
        uid = _normalize_uuid(user_id)
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            query = session.query(Notification).filter(Notification.user_id == uid)
            if unread_only:
                query = query.filter(Notification.is_read.is_(False))
            notifs = query.order_by(Notification.created_at.desc()).limit(limit).all()
            return [n.to_dict() for n in notifs]
        finally:
            if not session_provided:
                session.close()

    def mark_as_read(
        self,
        notification_id: str | uuid.UUID,
        user_id: str | uuid.UUID,
        db: Session | None = None,
    ) -> bool:
        """Marks a single notification as read."""
        nid = _normalize_uuid(notification_id)
        uid = _normalize_uuid(user_id)
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            notif = session.query(Notification).filter(
                Notification.id == nid,
                Notification.user_id == uid,
            ).first()
            if notif:
                notif.is_read = True
                if not session_provided:
                    session.commit()
                else:
                    session.flush()
                return True
            return False
        finally:
            if not session_provided:
                session.close()

    def mark_all_as_read(
        self,
        user_id: str | uuid.UUID,
        db: Session | None = None,
    ) -> int:
        """Marks all unread notifications of a user as read."""
        uid = _normalize_uuid(user_id)
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            count = session.query(Notification).filter(
                Notification.user_id == uid,
                Notification.is_read.is_(False),
            ).update({"is_read": True})
            if not session_provided:
                session.commit()
            else:
                session.flush()
            return count
        finally:
            if not session_provided:
                session.close()

    def delete_all_notifications(
        self,
        user_id: str | uuid.UUID,
        db: Session | None = None,
    ) -> int:
        """Deletes all notifications of a user."""
        uid = _normalize_uuid(user_id)
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            count = session.query(Notification).filter(Notification.user_id == uid).delete()
            if not session_provided:
                session.commit()
            else:
                session.flush()
            return count
        finally:
            if not session_provided:
                session.close()

    def get_unread_count(
        self,
        user_id: str | uuid.UUID,
        db: Session | None = None,
    ) -> int:
        """Gets count of unread notifications."""
        uid = _normalize_uuid(user_id)
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            return session.query(Notification).filter(
                Notification.user_id == uid,
                Notification.is_read.is_(False),
            ).count()
        finally:
            if not session_provided:
                session.close()


notification_service = NotificationService()
