"""MoodFeed SQLAlchemy Database Connection and Session Management."""

import logging
import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from backend.config import settings
from .models import Base

logger = logging.getLogger("moodfeed.db")

DATABASE_URL = settings.database_url if hasattr(settings, "database_url") else os.getenv(
    "DATABASE_URL",
    "sqlite:///./moodfeed_local.db",
)

connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
elif "postgresql" in DATABASE_URL:
    connect_args["connect_timeout"] = 2

engine = create_engine(
    DATABASE_URL,
    echo=False,
    future=True,
    connect_args=connect_args,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    future=True,
)

# Fallback SQLite engine for standalone local runs when PostgreSQL container is not started
_fallback_engine = None
_FallbackSessionLocal = None


def _ensure_sqlite_schema(eng) -> None:
    from sqlalchemy import inspect, text
    Base.metadata.create_all(bind=eng)
    try:
        insp = inspect(eng)
        if "user_preferences" in insp.get_table_names():
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

        if "users" in insp.get_table_names():
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

        if "posts" in insp.get_table_names():
            existing_post_cols = {c["name"] for c in insp.get_columns("posts")}
            post_cols_to_add = {
                "title": "TEXT",
                "author": "TEXT",
                "handle": "TEXT",
                "category": "TEXT DEFAULT 'Gündem'",
                "mood_score": "REAL DEFAULT 0.0",
                "mood_label": "TEXT DEFAULT 'neutral'",
                "sentiment_label": "TEXT DEFAULT 'neutral'",
                "sentiment_score": "REAL DEFAULT 0.5",
                "negativity_score": "REAL DEFAULT 0.1",
                "toxicity_score": "REAL DEFAULT 0.0",
                "repetition_score": "REAL DEFAULT 0.0",
                "language": "TEXT DEFAULT 'tr'",
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
    except Exception:
        pass

if DATABASE_URL.startswith("sqlite"):
    try:
        _ensure_sqlite_schema(engine)
    except Exception:
        pass


def _get_fallback_sessionmaker() -> sessionmaker:
    global _fallback_engine, _FallbackSessionLocal
    if _FallbackSessionLocal is None:
        _fallback_engine = create_engine(
            "sqlite:///moodfeed_local.db",
            echo=False,
            future=True,
            connect_args={"check_same_thread": False},
        )
        _ensure_sqlite_schema(_fallback_engine)
        _FallbackSessionLocal = sessionmaker(
            bind=_fallback_engine,
            autoflush=False,
            autocommit=False,
            future=True,
        )
    return _FallbackSessionLocal


def init_db() -> None:
    """Creates database tables if they do not exist."""
    try:
        Base.metadata.create_all(bind=engine)
        if DATABASE_URL.startswith("sqlite"):
            _ensure_sqlite_schema(engine)
        logger.info("Database initialized successfully: %s", DATABASE_URL)
    except Exception as e:
        logger.warning("Primary database unavailable (%s). Falling back to local SQLite.", e)
        _get_fallback_sessionmaker()


def get_db() -> Generator[Session, None, None]:
    """FastAPI database session dependency with resilient fallback."""
    db: Session | None = None
    try:
        db = SessionLocal()
        db.connection()
    except Exception:
        sm = _get_fallback_sessionmaker()
        db = sm()

    try:
        yield db
    finally:
        if db is not None:
            db.close()
