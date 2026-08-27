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
                "spiral_threshold": "REAL NOT NULL DEFAULT 0.7",
                "negative_threshold": "REAL NOT NULL DEFAULT 0.6",
                "positive_threshold": "REAL NOT NULL DEFAULT 0.5",
                "toxicity_threshold": "REAL NOT NULL DEFAULT 0.6",
                "theme": "VARCHAR(32) NOT NULL DEFAULT 'light'",
                "active_profile": "TEXT NOT NULL DEFAULT 'balanced'",
                "active_scenario": "TEXT NOT NULL DEFAULT 'default'",
                "profile_preset": "TEXT NOT NULL DEFAULT 'balanced'",
                "low_intensity_mode": "INTEGER NOT NULL DEFAULT 0",
                "muted_sources": "TEXT NOT NULL DEFAULT '[]'",
                "updated_at": "TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP",
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
                "avatar": "TEXT",
                "bio": "TEXT",
                "last_seen_at": "TIMESTAMP",
            }
            with eng.begin() as conn:
                for col_name, col_def in user_cols_to_add.items():
                    if col_name not in existing_user_cols:
                        try:
                            conn.execute(text(f"ALTER TABLE users ADD COLUMN {col_name} {col_def}"))
                        except Exception:
                            pass
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
