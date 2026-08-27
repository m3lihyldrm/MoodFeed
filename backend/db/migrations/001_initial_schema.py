"""Migration 001: Initial Database Schema.

PostgreSQL & SQLite migration creating the complete core schema:
- users
- user_preferences
- posts
- likes
- saves
- interaction_logs
"""

from __future__ import annotations

from typing import Any
from sqlalchemy import text
from backend.db.database import engine


def upgrade(bind: Any = None) -> None:
    """Creates the initial database tables and indexes."""
    target = bind or engine

    pg_ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id UUID PRIMARY KEY,
        email VARCHAR(255) UNIQUE,
        username VARCHAR(64) UNIQUE,
        password_hash VARCHAR(255),
        display_name VARCHAR(120),
        avatar VARCHAR(255),
        bio VARCHAR(500),
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        last_seen_at TIMESTAMPTZ
    );

    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id UUID PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        spiral_threshold FLOAT NOT NULL DEFAULT 0.7,
        negative_threshold FLOAT NOT NULL DEFAULT 0.6,
        positive_threshold FLOAT NOT NULL DEFAULT 0.5,
        toxicity_threshold FLOAT NOT NULL DEFAULT 0.6,
        theme VARCHAR(32) NOT NULL DEFAULT 'light',
        active_profile VARCHAR(64) NOT NULL DEFAULT 'balanced',
        active_scenario VARCHAR(64) NOT NULL DEFAULT 'default',
        profile_preset VARCHAR(32) NOT NULL DEFAULT 'balanced',
        low_intensity_mode BOOLEAN NOT NULL DEFAULT FALSE,
        muted_sources JSONB NOT NULL DEFAULT '[]'::jsonb,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS posts (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        title VARCHAR(255),
        author VARCHAR(120),
        handle VARCHAR(64),
        category VARCHAR(64) NOT NULL DEFAULT 'Gündem',
        sentiment_label VARCHAR(32) NOT NULL DEFAULT 'neutral',
        sentiment_score FLOAT NOT NULL DEFAULT 0.5,
        negativity_score FLOAT NOT NULL DEFAULT 0.1,
        toxicity_score FLOAT NOT NULL DEFAULT 0.0,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE TABLE IF NOT EXISTS likes (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, post_id)
    );

    CREATE TABLE IF NOT EXISTS saves (
        id UUID PRIMARY KEY,
        user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id UUID NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
        UNIQUE(user_id, post_id)
    );

    CREATE TABLE IF NOT EXISTS interaction_logs (
        id UUID PRIMARY KEY,
        user_id UUID REFERENCES users(id) ON DELETE CASCADE,
        event_type VARCHAR(64) NOT NULL,
        event_data JSONB NOT NULL DEFAULT '{}'::jsonb,
        created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
    );

    CREATE INDEX IF NOT EXISTS idx_posts_user_id ON posts(user_id);
    CREATE INDEX IF NOT EXISTS idx_posts_created_at ON posts(created_at DESC);
    CREATE INDEX IF NOT EXISTS idx_likes_post_id ON likes(post_id);
    CREATE INDEX IF NOT EXISTS idx_saves_user_id ON saves(user_id);
    """

    sqlite_ddl = """
    CREATE TABLE IF NOT EXISTS users (
        id TEXT PRIMARY KEY,
        email TEXT UNIQUE,
        username TEXT UNIQUE,
        password_hash TEXT,
        display_name TEXT,
        avatar TEXT,
        bio TEXT,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        last_seen_at TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS user_preferences (
        user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
        spiral_threshold REAL NOT NULL DEFAULT 0.7,
        negative_threshold REAL NOT NULL DEFAULT 0.6,
        positive_threshold REAL NOT NULL DEFAULT 0.5,
        toxicity_threshold REAL NOT NULL DEFAULT 0.6,
        theme VARCHAR(32) NOT NULL DEFAULT 'light',
        active_profile TEXT NOT NULL DEFAULT 'balanced',
        active_scenario TEXT NOT NULL DEFAULT 'default',
        profile_preset TEXT NOT NULL DEFAULT 'balanced',
        low_intensity_mode INTEGER NOT NULL DEFAULT 0,
        muted_sources TEXT NOT NULL DEFAULT '[]',
        updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS posts (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        content TEXT NOT NULL,
        title TEXT,
        author TEXT,
        handle TEXT,
        category TEXT NOT NULL DEFAULT 'Gündem',
        sentiment_label TEXT NOT NULL DEFAULT 'neutral',
        sentiment_score REAL NOT NULL DEFAULT 0.5,
        negativity_score REAL NOT NULL DEFAULT 0.1,
        toxicity_score REAL NOT NULL DEFAULT 0.0,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );

    CREATE TABLE IF NOT EXISTS likes (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, post_id)
    );

    CREATE TABLE IF NOT EXISTS saves (
        id TEXT PRIMARY KEY,
        user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        post_id TEXT NOT NULL REFERENCES posts(id) ON DELETE CASCADE,
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(user_id, post_id)
    );

    CREATE TABLE IF NOT EXISTS interaction_logs (
        id TEXT PRIMARY KEY,
        user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
        event_type TEXT NOT NULL,
        event_data TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
    );
    """

    try:
        with target.connect() as test_conn:
            pass
    except Exception:
        from sqlalchemy import create_engine
        target = create_engine(
            "sqlite:///moodfeed_local.db",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        print("PostgreSQL sunucusuna ulaşılamadı. Migration yerel SQLite veritabanına (moodfeed_local.db) uygulandı.")

    with target.begin() as conn:
        dialect = getattr(target, "dialect", None)
        dialect_name = dialect.name if dialect else "sqlite"
        if dialect_name == "postgresql":
            conn.execute(text(pg_ddl))
        else:
            for statement in sqlite_ddl.strip().split(";"):
                stmt = statement.strip()
                if stmt:
                    conn.execute(text(stmt))


def downgrade(bind: Any = None) -> None:
    """Drops all tables."""
    target = bind or engine
    with target.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS interaction_logs;"))
        conn.execute(text("DROP TABLE IF EXISTS likes;"))
        conn.execute(text("DROP TABLE IF EXISTS saves;"))
        conn.execute(text("DROP TABLE IF EXISTS posts;"))
        conn.execute(text("DROP TABLE IF EXISTS user_preferences;"))
        conn.execute(text("DROP TABLE IF EXISTS users;"))


if __name__ == "__main__":
    upgrade()
    print("Migration 001_initial_schema applied successfully.")
