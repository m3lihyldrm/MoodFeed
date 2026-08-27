"""SQLAlchemy Database Models for MoodFeed.

Re-exports User, UserPreferences, InteractionLog, and Base from backend.database.models
to maintain unified metadata and PostgreSQL entity definitions.
"""

from __future__ import annotations

from backend.database.models import Base, InteractionLog, Like, Post, Save, User, UserInteraction, UserPreferences

__all__ = ["Base", "User", "Post", "Like", "Save", "UserPreferences", "InteractionLog", "UserInteraction"]

