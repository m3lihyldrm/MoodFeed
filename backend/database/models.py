"""MoodFeed PostgreSQL / SQLAlchemy Database Models.

Defines User, Post, Like, Comment, Follow, Notification, UserPreferences,
UserInteraction, and InteractionLog entity models for persistent data storage.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class User(Base):
    """User account entity."""
    __tablename__ = "users"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=True, index=True)
    username = Column(String(64), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    display_name = Column(String(120), nullable=True)
    full_name = Column(String(120), nullable=True)
    avatar = Column(String(255), nullable=True)
    avatar_url = Column(String(255), nullable=True)
    bio = Column(String(500), nullable=True)
    is_verified = Column(Boolean, nullable=False, default=False)
    is_private = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    last_seen_at = Column(DateTime(timezone=True), nullable=True)

    preferences = relationship(
        "UserPreferences",
        back_populates="user",
        uselist=False,
        cascade="all, delete-orphan",
    )
    interaction_logs = relationship(
        "InteractionLog",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    posts = relationship(
        "Post",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    likes = relationship(
        "Like",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    saves = relationship(
        "Save",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    comments = relationship(
        "Comment",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    sent_follows = relationship(
        "Follow",
        foreign_keys="Follow.follower_user_id",
        back_populates="follower_user",
        cascade="all, delete-orphan",
    )
    received_follows = relationship(
        "Follow",
        foreign_keys="Follow.followed_user_id",
        back_populates="followed_user",
        cascade="all, delete-orphan",
    )
    notifications = relationship(
        "Notification",
        foreign_keys="Notification.user_id",
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def to_dict(self) -> dict[str, Any]:
        d_name = self.display_name or self.full_name or self.username or "Kullanıcı"
        av = self.avatar_url or self.avatar or (d_name[0].upper() if d_name else "👤")
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username or (self.email.split("@")[0] if self.email else "user"),
            "display_name": d_name,
            "full_name": self.full_name or d_name,
            "role": "admin" if (self.email and self.email.startswith("admin@")) else "user",
            "avatar": av,
            "avatar_url": av,
            "bio": self.bio or "",
            "is_verified": bool(self.is_verified),
            "is_private": bool(self.is_private),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "last_seen_at": self.last_seen_at.isoformat() if self.last_seen_at else None,
        }


class Post(Base):
    """User Post entity stored persistently in PostgreSQL."""
    __tablename__ = "posts"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    content = Column(String(2000), nullable=False)
    title = Column(String(255), nullable=True)
    author = Column(String(120), nullable=True)
    handle = Column(String(64), nullable=True)
    category = Column(String(64), nullable=False, default="Gündem")
    mood_score = Column(Float, nullable=False, default=0.0)  # -1.0 to 1.0
    mood_label = Column(String(32), nullable=False, default="neutral")  # happy, sad, angry, anxious, neutral
    sentiment_label = Column(String(32), nullable=False, default="neutral")
    sentiment_score = Column(Float, nullable=False, default=0.5)
    negativity_score = Column(Float, nullable=False, default=0.1)
    toxicity_score = Column(Float, nullable=False, default=0.0)
    repetition_score = Column(Float, nullable=False, default=0.0)
    language = Column(String(8), nullable=False, default="tr")
    is_published = Column(Boolean, nullable=False, default=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="posts")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    saves = relationship("Save", back_populates="post", cascade="all, delete-orphan")
    comments = relationship("Comment", back_populates="post", cascade="all, delete-orphan")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "content_id": str(self.id),
            "user_id": str(self.user_id),
            "content": self.content,
            "text": self.content,
            "title": self.title or (self.content[:40] + "..." if len(self.content) > 40 else self.content),
            "author": self.author or (self.user.display_name if self.user else "Kullanıcı"),
            "handle": self.handle or ("@" + (self.user.username if self.user and self.user.username else "kullanici")),
            "avatar": self.user.avatar if self.user and self.user.avatar else "👤",
            "category": self.category,
            "mood_score": float(self.mood_score),
            "mood_label": self.mood_label,
            "sentiment": {"label": self.sentiment_label, "score": float(self.sentiment_score)},
            "sentiment_label": self.sentiment_label,
            "sentiment_score": float(self.sentiment_score),
            "negativity_score": float(self.negativity_score),
            "toxicity_score": float(self.toxicity_score),
            "repetition_score": float(self.repetition_score),
            "language": self.language,
            "is_published": self.is_published,
            "likes_count": len(self.likes) if self.likes else 0,
            "saves_count": len(self.saves) if self.saves else 0,
            "comments_count": len([c for c in self.comments if not c.is_deleted]) if self.comments else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "time": "Az önce",
        }


class Like(Base):
    """Post Like entity."""
    __tablename__ = "likes"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_user_post_like"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = Column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="likes")
    post = relationship("Post", back_populates="likes")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "post_id": str(self.post_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "user": self.user.to_dict() if self.user else None,
        }


class Save(Base):
    """Post Bookmark/Save entity."""
    __tablename__ = "saves"
    __table_args__ = (UniqueConstraint("user_id", "post_id", name="uq_user_post_save"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = Column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="saves")
    post = relationship("Post", back_populates="saves")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "post_id": str(self.post_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class Comment(Base):
    """Comment entity supporting nested replies and mood scoring."""
    __tablename__ = "comments"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    post_id = Column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_comment_id = Column(
        Uuid,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content = Column(String(1000), nullable=False)
    mood_score = Column(Float, nullable=False, default=0.0)  # -1.0 to 1.0
    mood_label = Column(String(32), nullable=False, default="neutral")
    is_deleted = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="comments")
    post = relationship("Post", back_populates="comments")
    parent_comment = relationship("Comment", remote_side=[id], back_populates="replies")
    replies = relationship("Comment", back_populates="parent_comment", cascade="all, delete-orphan")

    def to_dict(self, include_replies: bool = True) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "post_id": str(self.post_id),
            "parent_comment_id": str(self.parent_comment_id) if self.parent_comment_id else None,
            "content": "[Bu yorum silindi]" if self.is_deleted else self.content,
            "mood_score": float(self.mood_score),
            "mood_label": self.mood_label,
            "is_deleted": self.is_deleted,
            "author": self.user.display_name if self.user else "Kullanıcı",
            "username": self.user.username if self.user else "kullanici",
            "avatar": self.user.avatar if self.user else "👤",
            "is_verified": self.user.is_verified if self.user else False,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
        if include_replies and self.replies:
            data["replies"] = [r.to_dict(include_replies=False) for r in self.replies if not r.is_deleted]
        else:
            data["replies"] = []
        return data


class Follow(Base):
    """User Follow relationship entity."""
    __tablename__ = "follows"
    __table_args__ = (UniqueConstraint("follower_user_id", "followed_user_id", name="uq_user_follow"),)

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    follower_user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    followed_user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    follower_user = relationship("User", foreign_keys=[follower_user_id], back_populates="sent_follows")
    followed_user = relationship("User", foreign_keys=[followed_user_id], back_populates="received_follows")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "follower_user_id": str(self.follower_user_id),
            "followed_user_id": str(self.followed_user_id),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "follower": self.follower_user.to_dict() if self.follower_user else None,
            "followed": self.followed_user.to_dict() if self.followed_user else None,
        }


class Notification(Base):
    """User Notification entity."""
    __tablename__ = "notifications"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    actor_user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    type = Column(String(32), nullable=False)  # "like", "comment", "follow", "mention"
    post_id = Column(
        Uuid,
        ForeignKey("posts.id", ondelete="CASCADE"),
        nullable=True,
    )
    comment_id = Column(
        Uuid,
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
    )
    is_read = Column(Boolean, nullable=False, default=False)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", foreign_keys=[user_id], back_populates="notifications")
    actor_user = relationship("User", foreign_keys=[actor_user_id])
    post = relationship("Post")
    comment = relationship("Comment")

    def to_dict(self) -> dict[str, Any]:
        actor_name = self.actor_user.display_name if self.actor_user else "Bir kullanıcı"
        messages = {
            "like": f"{actor_name} gönderinizi beğendi.",
            "comment": f"{actor_name} gönderinize yorum yaptı.",
            "follow": f"{actor_name} sizi takip etmeye başladı.",
            "mention": f"{actor_name} sizden bahsetti.",
        }
        return {
            "id": str(self.id),
            "user_id": str(self.user_id),
            "actor_user_id": str(self.actor_user_id) if self.actor_user_id else None,
            "actor": self.actor_user.to_dict() if self.actor_user else None,
            "type": self.type,
            "post_id": str(self.post_id) if self.post_id else None,
            "comment_id": str(self.comment_id) if self.comment_id else None,
            "message": messages.get(self.type, f"Yeni bildirim: {self.type}"),
            "is_read": bool(self.is_read),
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class UserPreferences(Base):
    """User Preferences entity stored persistently in PostgreSQL."""
    __tablename__ = "user_preferences"

    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        default=uuid.uuid4,
    )
    spiral_threshold = Column(Float, nullable=False, default=0.7)
    negative_threshold = Column(Float, nullable=False, default=0.6)
    positive_threshold = Column(Float, nullable=False, default=0.5)
    toxicity_threshold = Column(Float, nullable=False, default=0.6)
    theme = Column(String(32), nullable=False, default="light")
    active_profile = Column(String(64), nullable=False, default="balanced")
    active_scenario = Column(String(64), nullable=False, default="default")
    profile_preset = Column(String(32), nullable=False, default="balanced")
    low_intensity_mode = Column(Boolean, nullable=False, default=False)
    muted_sources = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=list,
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        onupdate=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="preferences")

    def to_dict(self) -> dict[str, Any]:
        return {
            "user_id": str(self.user_id),
            "spiral_threshold": float(self.spiral_threshold),
            "negative_threshold": float(self.negative_threshold),
            "positive_threshold": float(self.positive_threshold),
            "toxicity_threshold": float(self.toxicity_threshold),
            "theme": str(self.theme),
            "active_profile": str(self.active_profile),
            "active_scenario": str(self.active_scenario),
            "profile_preset": str(self.profile_preset or self.active_profile or "balanced"),
            "low_intensity_mode": bool(self.low_intensity_mode),
            "muted_sources": self.muted_sources or [],
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class UserInteraction(Base):
    """User explicit interaction entity (like, save, hide, less_like_this, mute_source)."""
    __tablename__ = "user_interactions"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    content_id = Column(String(255), nullable=False, index=True)
    action_type = Column(String(64), nullable=False, index=True)
    source = Column(String(120), nullable=True)
    category = Column(String(64), nullable=True)
    extra_data = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", backref="user_interactions")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "content_id": str(self.content_id),
            "action_type": str(self.action_type),
            "source": self.source,
            "category": self.category,
            "extra_data": self.extra_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class InteractionLog(Base):
    """Interaction audit log entity."""
    __tablename__ = "interaction_logs"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    user_id = Column(
        Uuid,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    event_type = Column(String(64), nullable=False)
    event_data = Column(
        JSON().with_variant(JSONB, "postgresql"),
        nullable=False,
        default=dict,
    )
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="interaction_logs")

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "user_id": str(self.user_id) if self.user_id else None,
            "event_type": self.event_type,
            "event_data": self.event_data or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
