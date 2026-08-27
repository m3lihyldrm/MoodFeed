"""MoodFeed PostgreSQL / SQLAlchemy Database Models.

Defines UserPreferences, User, and InteractionLog entity models for PostgreSQL persistence.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any
from sqlalchemy import Boolean, Column, DateTime, Float, ForeignKey, JSON, String, Uuid
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
    avatar = Column(String(255), nullable=True)
    bio = Column(String(500), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "email": self.email,
            "username": self.username or (self.email.split("@")[0] if self.email else "user"),
            "display_name": self.display_name or self.username or "Kullanıcı",
            "role": "admin" if (self.email and self.email.startswith("admin@")) else "user",
            "avatar": self.avatar or (self.display_name[0].upper() if self.display_name else "👤"),
            "bio": self.bio or "",
            "created_at": self.created_at.isoformat() if self.created_at else None,
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
    sentiment_label = Column(String(32), nullable=False, default="neutral")
    sentiment_score = Column(Float, nullable=False, default=0.5)
    negativity_score = Column(Float, nullable=False, default=0.1)
    toxicity_score = Column(Float, nullable=False, default=0.0)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.datetime.now(datetime.timezone.utc),
        nullable=False,
    )

    user = relationship("User", back_populates="posts")
    likes = relationship("Like", back_populates="post", cascade="all, delete-orphan")
    saves = relationship("Save", back_populates="post", cascade="all, delete-orphan")

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
            "sentiment": {"label": self.sentiment_label, "score": float(self.sentiment_score)},
            "sentiment_label": self.sentiment_label,
            "sentiment_score": float(self.sentiment_score),
            "negativity_score": float(self.negativity_score),
            "toxicity_score": float(self.toxicity_score),
            "likes_count": len(self.likes) if self.likes else 0,
            "saves_count": len(self.saves) if self.saves else 0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "time": "Az önce",
        }


class Like(Base):
    """Post Like entity."""
    __tablename__ = "likes"

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


class Save(Base):
    """Post Bookmark/Save entity."""
    __tablename__ = "saves"

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


class UserPreferences(Base):
    """User Preferences entity stored persistently in PostgreSQL.
    
    Fields:
    - user_id: UUID, Primary Key
    - spiral_threshold: Float
    - negative_threshold: Float
    - positive_threshold: Float
    - toxicity_threshold: Float
    - theme: String (e.g. 'light', 'dark')
    - updated_at: DateTime with timezone
    """
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

