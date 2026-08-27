"""Migration 002: Add UserPreferences Table.

PostgreSQL migration creating/updating user_preferences table with threshold and theme columns.
"""

from __future__ import annotations

from typing import Any
from sqlalchemy import text
from backend.db.database import engine


def upgrade(bind: Any = None) -> None:
    """Creates or upgrades the user_preferences table for PostgreSQL / SQLite."""
    target = bind or engine
    pg_ddl = """
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id UUID PRIMARY KEY,
        spiral_threshold FLOAT NOT NULL DEFAULT 0.7,
        negative_threshold FLOAT NOT NULL DEFAULT 0.6,
        positive_threshold FLOAT NOT NULL DEFAULT 0.5,
        toxicity_threshold FLOAT NOT NULL DEFAULT 0.6,
        theme VARCHAR(32) NOT NULL DEFAULT 'light',
        active_profile VARCHAR(64) NOT NULL DEFAULT 'balanced',
        active_scenario VARCHAR(64) NOT NULL DEFAULT 'default',
        profile_preset VARCHAR(32) NOT NULL DEFAULT 'balanced',
        muted_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );
    """
    sqlite_ddl = """
    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id TEXT PRIMARY KEY,
        spiral_threshold REAL NOT NULL DEFAULT 0.7,
        negative_threshold REAL NOT NULL DEFAULT 0.6,
        positive_threshold REAL NOT NULL DEFAULT 0.5,
        toxicity_threshold REAL NOT NULL DEFAULT 0.6,
        theme VARCHAR(32) NOT NULL DEFAULT 'light',
        active_profile TEXT NOT NULL DEFAULT 'balanced',
        active_scenario TEXT NOT NULL DEFAULT 'default',
        profile_preset TEXT NOT NULL DEFAULT 'balanced',
        muted_sources TEXT NOT NULL DEFAULT '[]',
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """
    with target.begin() as conn:
        dialect = getattr(target, "dialect", None)
        dialect_name = dialect.name if dialect else "sqlite"
        if dialect_name == "postgresql":
            conn.execute(text(pg_ddl))
        else:
            conn.execute(text(sqlite_ddl))


def downgrade(bind: Any = None) -> None:
    """Drops user_preferences table."""
    target = bind or engine
    with target.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS user_preferences;"))


if __name__ == "__main__":
    upgrade()
    print("Migration 002_add_user_preferences applied successfully.")
