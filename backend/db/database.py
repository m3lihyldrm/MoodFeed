"""MoodFeed SQLAlchemy Database Connection and Session Management."""

from __future__ import annotations

import logging
import os
from typing import Generator
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker
from backend.config import settings
from .models import Base

logger = logging.getLogger("moodfeed.db")

raw_db_url = getattr(settings, "database_url", None) or os.getenv(
    "DATABASE_URL",
    "sqlite:///./moodfeed_local.db",
)

if raw_db_url.startswith("postgres://"):
    raw_db_url = raw_db_url.replace("postgres://", "postgresql+psycopg2://", 1)

DATABASE_URL = raw_db_url

connect_args = {}
engine_kwargs: dict = {
    "echo": False,
    "future": True,
    "pool_pre_ping": True,
}

if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "postgresql" in DATABASE_URL:
    connect_args["connect_timeout"] = 10
    engine_kwargs["pool_recycle"] = 300

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    **engine_kwargs,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

# Fallback SQLite engine for resilient standalone local or serverless runs
_fallback_engine = None
_FallbackSessionLocal = None


def _ensure_schema_columns_and_indexes(eng) -> None:
    """Idempotently ensures all tables, columns, and indexes exist on the target engine."""
    try:
        Base.metadata.create_all(bind=eng)
        insp = inspect(eng)
        existing_tables = set(insp.get_table_names())

        if "user_preferences" in existing_tables:
            existing_cols = {c["name"] for c in insp.get_columns("user_preferences")}
            cols_to_add = {
                "spiral_threshold": "REAL DEFAULT 0.7",
                "negative_threshold": "REAL DEFAULT 0.6",
                "positive_threshold": "REAL DEFAULT 0.5",
                "toxicity_threshold": "REAL DEFAULT 0.6",
                "theme": "VARCHAR(32) DEFAULT 'light'",
                "active_profile": "TEXT DEFAULT 'balanced'",
                "active_scenario": "TEXT DEFAULT 'default'",
                "profile_preset": "TEXT DEFAULT 'balanced'",
                "low_intensity_mode": "INTEGER DEFAULT 0",
                "muted_sources": "TEXT DEFAULT '[]'",
                "updated_at": "TIMESTAMP",
            }
            with eng.begin() as conn:
                for col_name, col_def in cols_to_add.items():
                    if col_name not in existing_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE user_preferences ADD COLUMN {col_name} {col_def}"))
                        except Exception:
                            pass

        if "users" in existing_tables:
            existing_user_cols = {c["name"] for c in insp.get_columns("users")}
            user_cols_to_add = {
                "email": "TEXT",
                "username": "TEXT",
                "password_hash": "TEXT",
                "display_name": "TEXT",
                "full_name": "TEXT",
                "avatar": "TEXT",
                "avatar_url": "TEXT",
                "bio": "TEXT",
                "is_verified": "INTEGER DEFAULT 0",
                "is_private": "INTEGER DEFAULT 0",
                "created_at": "TIMESTAMP",
                "updated_at": "TIMESTAMP",
                "last_seen_at": "TIMESTAMP",
            }
            with eng.begin() as conn:
                for col_name, col_def in user_cols_to_add.items():
                    if col_name not in existing_user_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        except Exception:
                            pass

        if "posts" in existing_tables:
            existing_post_cols = {c["name"] for c in insp.get_columns("posts")}
            post_cols_to_add = {
                "title": "TEXT",
                "author": "TEXT",
                "handle": "TEXT",
                "category": "TEXT DEFAULT 'Gündem'",
                "source_name": "TEXT",
                "source_url": "TEXT",
                "original_url": "TEXT",
                "image_url": "TEXT",
                "published_at": "TIMESTAMP",
                "fetched_at": "TIMESTAMP",
                "normalized_title": "TEXT",
                "content_hash": "TEXT",
                "mood_score": "REAL DEFAULT 0.0",
                "mood_label": "TEXT DEFAULT 'neutral'",
                "mood_distribution": "TEXT DEFAULT '{}'",
                "sentiment_label": "TEXT DEFAULT 'neutral'",
                "sentiment_score": "REAL DEFAULT 0.5",
                "negativity_score": "REAL DEFAULT 0.1",
                "toxicity_score": "REAL DEFAULT 0.0",
                "spam_score": "REAL DEFAULT 0.0",
                "bot_risk": "TEXT DEFAULT 'low'",
                "repetition_score": "REAL DEFAULT 0.0",
                "language": "TEXT DEFAULT 'tr'",
                "metadata_json": "TEXT DEFAULT '{}'",
                "is_published": "INTEGER DEFAULT 1",
                "created_at": "TIMESTAMP",
                "updated_at": "TIMESTAMP",
            }
            with eng.begin() as conn:
                for col_name, col_def in post_cols_to_add.items():
                    if col_name not in existing_post_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE posts ADD COLUMN {col_name} {col_def}"))
                        except Exception:
                            pass

                # Idempotent index creation
                index_stmts = [
                    "CREATE INDEX IF NOT EXISTS ix_posts_original_url ON posts(original_url);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_normalized_title ON posts(normalized_title);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_content_hash ON posts(content_hash);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_mood_label ON posts(mood_label);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_category ON posts(category);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_published_at ON posts(published_at);",
                    "CREATE INDEX IF NOT EXISTS ix_posts_created_at ON posts(created_at);",
                ]
                for stmt in index_stmts:
                    try:
                        conn.execute(text(stmt))
                    except Exception:
                        pass
    except Exception as err:
        logger.debug("Schema verification warning: %s", err)


def _get_fallback_sessionmaker() -> sessionmaker:
    """Returns singleton sessionmaker for persistent local SQLite fallback."""
    global _fallback_engine, _FallbackSessionLocal
    if _FallbackSessionLocal is None:
        db_path = "/tmp/moodfeed_local.db" if (os.getenv("VERCEL") == "1" or os.name != "nt") else "moodfeed_local.db"
        _fallback_engine = create_engine(
            f"sqlite:///{db_path}",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        _ensure_schema_columns_and_indexes(_fallback_engine)
        _FallbackSessionLocal = sessionmaker(
            bind=_fallback_engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _FallbackSessionLocal


def get_storage_mode() -> str:
    """Returns the currently active storage backend mode ('postgresql', 'sqlite', or 'sqlite_fallback')."""
    if DATABASE_URL.startswith("sqlite"):
        return "sqlite"
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return "postgresql"
    except Exception:
        return "sqlite_fallback"


def get_db_session() -> Session:
    """Returns an active, tested SQLAlchemy database session with automatic SQLite fallback."""
    try:
        session = SessionLocal()
        # Test connection validity
        session.execute(text("SELECT 1"))
        return session
    except Exception as e:
        logger.debug("Primary database session failed, using fallback session: %s", e)
        fallback_sm = _get_fallback_sessionmaker()
        return fallback_sm()


def init_db() -> None:
    """Idempotently initializes primary database tables, columns, and indexes with resilient fallback."""
    try:
        _ensure_schema_columns_and_indexes(engine)
        storage = get_storage_mode()
        logger.info("Database initialized successfully (Storage Mode: %s)", storage)
    except Exception as e:
        logger.warning("Primary database initialization error (%s). Falling back to local SQLite.", e)
        _ensure_schema_columns_and_indexes(_get_fallback_sessionmaker().kw["bind"])


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency yielding an active session with resilient fallback."""
    db: Session | None = None
    try:
        db = get_db_session()
        yield db
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
