"""MoodFeed User Authentication and Session Service.

Provides user registration, password verification, JWT token issuance,
and persistent User model management in PostgreSQL / SQLite fallback.
"""

from __future__ import annotations

import datetime
import uuid
from typing import Any
from sqlalchemy.orm import Session
from backend.auth.security import create_jwt_token, hash_password, verify_jwt_token, verify_password
from backend.config import settings
from backend.database.models import User, UserPreferences
from backend.db.database import get_db, _get_fallback_sessionmaker


def _normalize_uuid(val: uuid.UUID | str) -> uuid.UUID:
    if isinstance(val, uuid.UUID):
        return val
    try:
        return uuid.UUID(str(val))
    except Exception:
        return uuid.uuid5(uuid.NAMESPACE_DNS, str(val))


class PersistentAuthService:
    """Production authentication service backed by SQLAlchemy / PostgreSQL."""

    def register(
        self,
        email: str,
        password: str,
        username: str | None = None,
        display_name: str | None = None,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Registers a new user and returns user info + JWT token."""
        clean_email = email.strip().lower()
        if len(password) < 6:
            raise ValueError("Parola en az 6 karakter uzunluğunda olmalıdır.")

        clean_username = (username or clean_email.split("@")[0]).strip()
        clean_display = (display_name or clean_username).strip()

        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            # Check existing
            existing = session.query(User).filter(
                (User.email == clean_email) | (User.username == clean_username)
            ).first()
            if existing:
                if existing.email == clean_email:
                    raise ValueError("Bu e-posta adresiyle kayıtlı bir hesap zaten var.")
                raise ValueError("Bu kullanıcı adı zaten alınmış.")

            user_id = uuid.uuid4()
            pwd_hash = hash_password(password)
            user = User(
                id=user_id,
                email=clean_email,
                username=clean_username,
                password_hash=pwd_hash,
                display_name=clean_display,
                avatar=clean_display[0].upper() if clean_display else "👤",
                bio="MoodFeed kullanıcısı",
                created_at=datetime.datetime.now(datetime.timezone.utc),
            )
            session.add(user)

            # Also create default preferences
            prefs = UserPreferences(
                user_id=user_id,
                spiral_threshold=0.7,
                negative_threshold=0.6,
                positive_threshold=0.5,
                toxicity_threshold=0.6,
                theme="dark",
                active_profile="balanced",
                active_scenario="default",
                profile_preset="balanced",
            )
            session.add(prefs)
            session.commit()
            session.refresh(user)

            token = create_jwt_token(
                {"sub": str(user.id), "email": user.email, "username": user.username},
                settings.jwt_secret,
                ttl_seconds=86400 * 7,
            )

            return {
                "user": user.to_dict(),
                "access_token": token,
                "token_type": "bearer",
                "message": "Kayıt başarılı.",
            }
        finally:
            if not session_provided:
                session.close()

    def login(
        self,
        email: str,
        password: str,
        db: Session | None = None,
    ) -> dict[str, Any]:
        """Authenticates user with email/username and password."""
        clean_email = email.strip().lower()
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            user = session.query(User).filter(
                (User.email == clean_email) | (User.username == clean_email)
            ).first()
            if not user or not user.password_hash or not verify_password(password, user.password_hash):
                raise ValueError("Geçersiz e-posta veya parola.")

            user.last_seen_at = datetime.datetime.now(datetime.timezone.utc)
            session.commit()

            token = create_jwt_token(
                {"sub": str(user.id), "email": user.email, "username": user.username},
                settings.jwt_secret,
                ttl_seconds=86400 * 7,
            )

            return {
                "user": user.to_dict(),
                "access_token": token,
                "token_type": "bearer",
                "message": "Giriş başarılı.",
            }
        finally:
            if not session_provided:
                session.close()

    def get_user_by_email(
        self,
        email: str,
        db: Session | None = None,
    ) -> dict[str, Any] | None:
        """Finds user by email."""
        clean_email = email.strip().lower()
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            user = session.query(User).filter(User.email == clean_email).first()
            return user.to_dict() if user else None
        finally:
            if not session_provided:
                session.close()

    def get_user_by_id(
        self,
        user_id: uuid.UUID | str,
        db: Session | None = None,
    ) -> dict[str, Any] | None:
        """Finds user by ID."""
        uid = _normalize_uuid(user_id)
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            user = session.query(User).filter(User.id == uid).first()
            return user.to_dict() if user else None
        finally:
            if not session_provided:
                session.close()


    def get_current_user_from_token(
        self,
        token: str,
        db: Session | None = None,
    ) -> dict[str, Any] | None:
        """Decodes either a Clerk session token or a local JWT token and returns User entity dict."""
        if not token or not isinstance(token, str):
            return None

        # 1. Check if token is a Clerk Session Token
        try:
            from backend.auth.clerk import verify_clerk_token, get_or_sync_clerk_user
            clerk_payload = verify_clerk_token(token)
            if clerk_payload and "sub" in clerk_payload:
                return get_or_sync_clerk_user(clerk_payload, db=db)
        except Exception:
            pass

        # 2. Check if token is a Local JWT Token
        payload = verify_jwt_token(token, settings.jwt_secret)
        if not payload or "sub" not in payload:
            return None

        uid = _normalize_uuid(payload["sub"])
        session_provided = db is not None
        session = db if session_provided else _get_fallback_sessionmaker()()

        try:
            user = session.query(User).filter(User.id == uid).first()
            if not user:
                return None
            user_dict = user.to_dict()
            user_dict["auth_provider"] = "local"
            return user_dict
        finally:
            if not session_provided:
                session.close()

    def get_current_user(
        self,
        token: str,
        db: Session | None = None,
    ) -> dict[str, Any] | None:
        """Alias for get_current_user_from_token."""
        return self.get_current_user_from_token(token, db=db)


auth_service_instance = PersistentAuthService()
auth_service = auth_service_instance
