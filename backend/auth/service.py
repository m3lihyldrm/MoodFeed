"""MoodFeed Authentication & Authorization Service.

Implements user registration, authentication, session issuance, token rotation,
current user resolution, and role-based access control.
"""

from __future__ import annotations

import time
import uuid
from typing import Any
from backend.auth.security import create_jwt_token, hash_password, verify_jwt_token, verify_password
from backend.config import settings
from backend.database.repository import repository


class AuthService:
    """Production authentication service with brute-force defense."""

    def __init__(self) -> None:
        self.failed_attempts: dict[str, list[float]] = {}  # email -> timestamps

    def is_rate_limited(self, email: str) -> bool:
        now = time.time()
        attempts = self.failed_attempts.get(email, [])
        # Only consider attempts in the last 15 minutes (900s)
        recent = [t for t in attempts if now - t < 900]
        self.failed_attempts[email] = recent
        return len(recent) >= 5

    def record_failed_attempt(self, email: str) -> None:
        now = time.time()
        if email not in self.failed_attempts:
            self.failed_attempts[email] = []
        self.failed_attempts[email].append(now)

    def register(self, email: str, password: str, display_name: str, role: str = "user") -> dict[str, Any]:
        """Registers a new user and returns user info + tokens."""
        if len(password) < 8:
            raise ValueError("Parola en az 8 karakter uzunluğunda olmalıdır.")

        existing = repository.get_user_by_email(email)
        if existing:
            raise ValueError("Bu e-posta adresiyle kayıtlı bir hesap zaten var.")

        password_hash = hash_password(password)
        user = repository.create_user(email, password_hash, display_name, role)

        session = repository.create_session(user["id"])
        access_token = create_jwt_token(
            {"sub": user["id"], "role": user["role"], "email": user["email"]},
            settings.jwt_secret,
            ttl_seconds=settings.access_token_ttl_minutes * 60,
        )
        refresh_token = create_jwt_token(
            {"sub": user["id"], "session_id": session["id"], "type": "refresh"},
            settings.jwt_secret,
            ttl_seconds=settings.refresh_token_ttl_days * 86400,
        )

        repository.log_audit_event(user["id"], "USER_REGISTER", "users", user["id"], "success")
        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "display_name": user["display_name"],
                "role": user["role"],
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_ttl_minutes * 60,
        }

    def login(self, email: str, password: str, user_agent: str | None = None, ip_address: str | None = None) -> dict[str, Any]:
        """Authenticates user with password and issues session tokens."""
        clean_email = email.strip().lower()
        if self.is_rate_limited(clean_email):
            repository.log_audit_event(None, "LOGIN_RATE_LIMITED", "users", clean_email, "denied")
            raise ValueError("Çok fazla başarısız giriş denemesi. Lütfen 15 dakika sonra tekrar deneyin.")

        user = repository.get_user_by_email(clean_email)
        if not user or not verify_password(password, user["password_hash"]):
            self.record_failed_attempt(clean_email)
            repository.log_audit_event(user["id"] if user else None, "LOGIN_FAILED", "users", clean_email, "failure")
            raise ValueError("Geçersiz e-posta veya parola.")

        # Clear failed attempts on success
        if clean_email in self.failed_attempts:
            del self.failed_attempts[clean_email]

        session = repository.create_session(user["id"], user_agent, ip_address)
        access_token = create_jwt_token(
            {"sub": user["id"], "role": user["role"], "email": user["email"]},
            settings.jwt_secret,
            ttl_seconds=settings.access_token_ttl_minutes * 60,
        )
        refresh_token = create_jwt_token(
            {"sub": user["id"], "session_id": session["id"], "type": "refresh"},
            settings.jwt_secret,
            ttl_seconds=settings.refresh_token_ttl_days * 86400,
        )

        repository.log_audit_event(user["id"], "USER_LOGIN", "users", user["id"], "success")
        return {
            "user": {
                "id": user["id"],
                "email": user["email"],
                "display_name": user["display_name"],
                "role": user["role"],
            },
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_ttl_minutes * 60,
        }

    def refresh(self, refresh_token: str) -> dict[str, Any]:
        """Rotates refresh token and issues new access token."""
        payload = verify_jwt_token(refresh_token, settings.jwt_secret)
        if not payload or payload.get("type") != "refresh":
            raise ValueError("Geçersiz veya süresi dolmuş yenileme anahtarı.")

        user_id = payload["sub"]
        session_id = payload.get("session_id")
        user = repository.get_user_by_id(user_id)
        if not user or not user["is_active"]:
            raise ValueError("Kullanıcı bulunamadı veya hesap devre dışı bırakılmış.")

        # Issue fresh access token and rotated refresh token
        new_access_token = create_jwt_token(
            {"sub": user["id"], "role": user["role"], "email": user["email"]},
            settings.jwt_secret,
            ttl_seconds=settings.access_token_ttl_minutes * 60,
        )
        new_refresh_token = create_jwt_token(
            {"sub": user["id"], "session_id": session_id, "type": "refresh"},
            settings.jwt_secret,
            ttl_seconds=settings.refresh_token_ttl_days * 86400,
        )
        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": settings.access_token_ttl_minutes * 60,
        }

    def logout(self, user_id: str, session_id: str | None = None) -> bool:
        """Revokes active session."""
        if session_id:
            repository.revoke_session(session_id)
        else:
            repository.revoke_all_user_sessions(user_id)
        repository.log_audit_event(user_id, "USER_LOGOUT", "sessions", session_id, "success")
        return True

    def get_current_user_from_token(self, token: str) -> dict[str, Any] | None:
        """Validates Bearer token and resolves active user."""
        payload = verify_jwt_token(token, settings.jwt_secret)
        if not payload or not payload.get("sub"):
            return None
        user = repository.get_user_by_id(payload["sub"])
        if not user or not user.get("is_active"):
            return None
        return user


# Singleton auth service instance
auth_service = AuthService()
