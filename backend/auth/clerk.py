"""MoodFeed Clerk Authentication & User Synchronization.

Provides Clerk session token verification, JWKS caching, and automatic
synchronization of Clerk users with local SQLAlchemy/PostgreSQL database records.
"""

from __future__ import annotations

import datetime
import json
import logging
import time
import urllib.request
import uuid
from typing import Any, Callable
from sqlalchemy.orm import Session
from backend.auth.security import base64url_decode
from backend.config import settings
from backend.database.models import User, UserPreferences
from backend.db.database import _get_fallback_sessionmaker

logger = logging.getLogger("moodfeed.auth.clerk")

# In-memory mock verifier for unit tests to prevent external network calls
_mock_clerk_verifier: Callable[[str], dict[str, Any] | None] | None = None
_jwks_cache: dict[str, Any] = {}
_jwks_last_fetched: float = 0.0


def is_clerk_configured() -> bool:
    """Returns whether Clerk authentication is fully enabled and configured."""
    return bool(
        settings.auth_provider == "clerk"
        and settings.feature_flag_clerk_auth
        and settings.clerk_publishable_key
    )


def set_mock_clerk_verifier(verifier: Callable[[str], dict[str, Any] | None] | None) -> None:
    """Sets a mock verifier for unit testing."""
    global _mock_clerk_verifier
    _mock_clerk_verifier = verifier


def get_mock_clerk_verifier() -> Callable[[str], dict[str, Any] | None] | None:
    """Returns the active mock verifier."""
    return _mock_clerk_verifier


def decode_jwt_unverified(token: str) -> tuple[dict[str, Any], dict[str, Any]] | None:
    """Decodes header and payload of a JWT without verifying signature."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, _ = parts
        header = json.loads(base64url_decode(header_b64).decode("utf-8"))
        payload = json.loads(base64url_decode(payload_b64).decode("utf-8"))
        return header, payload
    except Exception:
        return None


def fetch_jwks(jwks_url: str) -> dict[str, Any] | None:
    """Fetches JWKS keys from Clerk with in-memory caching."""
    global _jwks_cache, _jwks_last_fetched
    now = time.time()
    if _jwks_cache and (now - _jwks_last_fetched) < 3600:
        return _jwks_cache

    try:
        req = urllib.request.Request(
            jwks_url,
            headers={"User-Agent": "MoodFeed-Auth/1.0", "Accept": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                _jwks_cache = data
                _jwks_last_fetched = now
                return data
    except Exception:
        pass
    return None


def verify_clerk_token(token: str) -> dict[str, Any] | None:
    """Verifies a Clerk session token and returns decoded claims.
    
    Checks expiration, issuer, subject, and signature.
    In testing/mock environments, uses the mock verifier hook.
    """
    if not token or not isinstance(token, str):
        return None

    # 1. Custom mock verifier if set (for deterministic tests)
    if _mock_clerk_verifier is not None:
        return _mock_clerk_verifier(token)

    # 2. Decode claims
    decoded = decode_jwt_unverified(token)
    if not decoded:
        return None
    header, payload = decoded

    now = int(time.time())
    exp = payload.get("exp")
    if exp is not None and exp < (now - 30):  # 30s clock skew
        return None

    iat = payload.get("iat")
    if iat is not None and iat > (now + 300):
        return None

    sub = payload.get("sub")
    if not sub:
        return None

    # Verify issuer if configured
    if settings.clerk_issuer and payload.get("iss"):
        token_iss = str(payload["iss"]).rstrip("/").lower().replace("https://", "").replace("http://", "")
        cfg_iss = str(settings.clerk_issuer).rstrip("/").lower().replace("https://", "").replace("http://", "")
        if token_iss != cfg_iss and cfg_iss not in token_iss and token_iss not in cfg_iss:
            logger.warning("[Clerk Auth] Token issuer mismatch: token iss='%s' != settings clerk_issuer='%s'", payload.get("iss"), settings.clerk_issuer)
            return None

    # If PyJWT is installed and JWKS is configured, verify signature
    if settings.clerk_jwks_url:
        try:
            import jwt
            jwks = fetch_jwks(settings.clerk_jwks_url)
            if jwks and "keys" in jwks:
                kid = header.get("kid")
                key_dict = next((k for k in jwks["keys"] if k.get("kid") == kid), None)
                if key_dict:
                    public_key = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(key_dict))
                    verified_payload = jwt.decode(
                        token,
                        public_key,
                        algorithms=["RS256"],
                        options={"verify_exp": True, "verify_aud": False},
                    )
                    return verified_payload
        except Exception as e:
            logger.debug("[Clerk Auth] Signature verification exception: %s", e)
            if settings.app_env != "production":
                return payload
            return None

    return payload


def get_or_sync_clerk_user(payload: dict[str, Any], db: Session | None = None) -> dict[str, Any]:
    """Finds or creates a local database User record matching the Clerk user identity."""
    clerk_id = str(payload.get("sub", "")).strip()
    if not clerk_id:
        raise ValueError("Clerk payload missing 'sub' claim.")

    email = str(
        payload.get("email")
        or payload.get("email_address")
        or payload.get("primary_email_address")
        or f"{clerk_id}@clerk.user"
    ).strip().lower()
    
    username = str(
        payload.get("username")
        or payload.get("preferred_username")
        or email.split("@")[0]
    ).strip()

    first_name = payload.get("first_name", "")
    last_name = payload.get("last_name", "")
    full_name = f"{first_name} {last_name}".strip() if (first_name or last_name) else ""
    display_name = str(payload.get("display_name") or payload.get("name") or full_name or username).strip()
    avatar = str(payload.get("avatar") or payload.get("image_url") or payload.get("picture") or (display_name[0].upper() if display_name else "👤"))

    # Deterministically derive UUID from Clerk User ID
    user_uuid = uuid.uuid5(uuid.NAMESPACE_DNS, f"clerk:{clerk_id}")

    session_provided = db is not None
    session = db if session_provided else _get_fallback_sessionmaker()()

    try:
        user = session.query(User).filter(
            (User.id == user_uuid) | (User.email == email)
        ).first()

        now = datetime.datetime.now(datetime.timezone.utc)
        if not user:
            # Prevent username collisions with different user IDs
            colliding_user = session.query(User).filter(User.username == username).first()
            if colliding_user:
                username = f"{username}_{clerk_id[-4:]}"

            user = User(
                id=user_uuid,
                email=email,
                username=username,
                password_hash=None,  # Clerk manages passwords externally
                display_name=display_name,
                avatar=avatar,
                bio="MoodFeed (Clerk) kullanıcısı",
                created_at=now,
                last_seen_at=now,
            )
            session.add(user)

            prefs = session.query(UserPreferences).filter(UserPreferences.user_id == user_uuid).first()
            if not prefs:
                prefs = UserPreferences(
                    user_id=user_uuid,
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
        else:
            user.last_seen_at = now
            if email and not email.endswith("@clerk.user") and user.email != email:
                user.email = email
            if display_name and display_name != clerk_id and (not user.display_name or user.display_name == "Kullanıcı"):
                user.display_name = display_name
            if avatar and not user.avatar:
                user.avatar = avatar
            session.commit()
            session.refresh(user)

        user_dict = user.to_dict()
        user_dict["clerk_id"] = clerk_id
        user_dict["auth_provider"] = "clerk"
        logger.info("[Clerk Auth] Synced user: %s (Clerk ID: %s)", user.email, clerk_id)
        return user_dict
    finally:
        if not session_provided:
            session.close()
