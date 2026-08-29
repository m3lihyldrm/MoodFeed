"""Migration 004: Enhance Posts Table for RSS Archive and Deduplication.

Adds source_name, source_url, original_url, image_url, published_at,
fetched_at, normalized_title, content_hash, mood_label, mood_score,
mood_distribution, spam_score, bot_risk, metadata_json and appropriate indexes.
"""

from __future__ import annotations

from typing import Any
from sqlalchemy import inspect, text
from backend.db.database import engine


def upgrade(bind: Any = None) -> None:
    """Applies schema additions for posts table on PostgreSQL / SQLite."""
    target = bind or engine

    with target.begin() as conn:
        dialect = getattr(target, "dialect", None)
        dialect_name = dialect.name if dialect else "sqlite"

        if dialect_name == "postgresql":
            ddl_statements = [
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS source_name VARCHAR(120);",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS source_url VARCHAR(500);",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS original_url VARCHAR(500);",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS published_at TIMESTAMPTZ;",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS fetched_at TIMESTAMPTZ DEFAULT NOW();",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS normalized_title VARCHAR(255);",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS content_hash VARCHAR(64);",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS mood_label VARCHAR(32) NOT NULL DEFAULT 'neutral';",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS mood_score FLOAT NOT NULL DEFAULT 0.0;",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS mood_distribution JSONB DEFAULT '{}';",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS spam_score FLOAT NOT NULL DEFAULT 0.0;",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS bot_risk VARCHAR(32) NOT NULL DEFAULT 'low';",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS metadata_json JSONB DEFAULT '{}';",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS is_published BOOLEAN NOT NULL DEFAULT TRUE;",
                "ALTER TABLE posts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ DEFAULT NOW();",
                "CREATE INDEX IF NOT EXISTS ix_posts_original_url ON posts(original_url);",
                "CREATE INDEX IF NOT EXISTS ix_posts_normalized_title ON posts(normalized_title);",
                "CREATE INDEX IF NOT EXISTS ix_posts_content_hash ON posts(content_hash);",
                "CREATE INDEX IF NOT EXISTS ix_posts_mood_label ON posts(mood_label);",
                "CREATE INDEX IF NOT EXISTS ix_posts_category ON posts(category);",
                "CREATE INDEX IF NOT EXISTS ix_posts_published_at ON posts(published_at);",
            ]
            for stmt in ddl_statements:
                try:
                    conn.execute(text(stmt))
                except Exception:
                    pass
        else:
            insp = inspect(target)
            if "posts" in insp.get_table_names():
                existing = {c["name"] for c in insp.get_columns("posts")}
                cols = {
                    "source_name": "TEXT",
                    "source_url": "TEXT",
                    "original_url": "TEXT",
                    "image_url": "TEXT",
                    "published_at": "TIMESTAMP",
                    "fetched_at": "TIMESTAMP",
                    "normalized_title": "TEXT",
                    "content_hash": "TEXT",
                    "mood_label": "TEXT DEFAULT 'neutral'",
                    "mood_score": "REAL DEFAULT 0.0",
                    "mood_distribution": "TEXT DEFAULT '{}'",
                    "spam_score": "REAL DEFAULT 0.0",
                    "bot_risk": "TEXT DEFAULT 'low'",
                    "metadata_json": "TEXT DEFAULT '{}'",
                    "is_published": "INTEGER DEFAULT 1",
                    "updated_at": "TIMESTAMP",
                }
                for col_name, col_type in cols.items():
                    if col_name not in existing:
                        try:
                            conn.execute(text(f"ALTER TABLE posts ADD COLUMN {col_name} {col_type}"))
                        except Exception:
                            pass
                index_stmts = [
                    "CREATE INDEX IF NOT EXISTS ix_posts_original_url ON posts(original_url);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_normalized_title ON posts(normalized_title);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_content_hash ON posts(content_hash);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_mood_label ON posts(mood_label);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_category ON posts(category);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_published_at ON posts(published_at);",
                ]
                for stmt in index_stmts:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass


def downgrade(bind: Any = None) -> None:
    """Downgrade helper."""
    pass


if __name__ == "__main__":
    upgrade()
    print("Migration 004_enhance_posts_rss_archive applied successfully.")
