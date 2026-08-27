"""Migration 003: Add Users, Posts, Likes, and Saves Tables.

PostgreSQL migration creating/updating users, posts, likes, and saves tables.
"""

from __future__ import annotations

from typing import Any
from sqlalchemy import text
from backend.db.database import engine


def upgrade(bind: Any = None) -> None:
    """Creates users, posts, likes, and saves tables for PostgreSQL / SQLite."""
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
    """

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
    """Drops likes, saves, posts, and users tables."""
    target = bind or engine
    with target.begin() as conn:
        conn.execute(text("DROP TABLE IF EXISTS likes;"))
        conn.execute(text("DROP TABLE IF EXISTS saves;"))
        conn.execute(text("DROP TABLE IF EXISTS posts;"))


if __name__ == "__main__":
    upgrade()
    print("Migration 003_add_users_posts applied successfully.")
