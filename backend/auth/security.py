"""MoodFeed Security & Authentication Cryptographic Utilities.

Provides password hashing, constant-time verification, JWT creation,
signature verification, and token rotation protection.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any
from backend.config import settings


def generate_salt(length: int = 16) -> str:
    """Generates a cryptographically strong random salt hex string."""
    return os.urandom(length).hex()


def hash_password(password: str, salt: str | None = None) -> str:
    """Hashes a plaintext password using PBKDF2-HMAC-SHA256 with 600,000 iterations."""
    if not salt:
        salt = generate_salt(16)
    # Use 600,000 iterations for OWASP compliance
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        600000,
        dklen=32,
    )
    return f"pbkdf2:sha256:600000${salt}${key.hex()}"


def verify_password(password: str, password_hash: str) -> bool:
    """Constant-time verification of plaintext password against stored hash."""
    try:
        parts = password_hash.split("$")
        if len(parts) != 3:
            return False
        meta, salt, stored_key = parts
        _, algo, iterations_str = meta.split(":")
        iterations = int(iterations_str)
        key = hashlib.pbkdf2_hmac(
            algo,
            password.encode("utf-8"),
            salt.encode("utf-8"),
            iterations,
            dklen=32,
        )
        return hmac.compare_digest(key.hex(), stored_key)
    except Exception:
        return False


def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b"=").decode("utf-8")


def base64url_decode(data: str) -> bytes:
    padding = b"=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else b""
    return base64.urlsafe_b64decode(data.encode("utf-8") + padding)


def create_jwt_token(payload: dict[str, Any], secret: str, ttl_seconds: int = 1800) -> str:
    """Creates a signed HMAC-SHA256 JWT."""
    now = int(time.time())
    header = {"typ": "JWT", "alg": "HS256"}
    full_payload = {**payload, "iat": now, "exp": now + ttl_seconds}

    header_b64 = base64url_encode(json.dumps(header, separators=(",", ":")).encode("utf-8"))
    payload_b64 = base64url_encode(json.dumps(full_payload, separators=(",", ":")).encode("utf-8"))
    signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

    signature = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    signature_b64 = base64url_encode(signature)

    return f"{header_b64}.{payload_b64}.{signature_b64}"


def verify_jwt_token(token: str, secret: str) -> dict[str, Any] | None:
    """Verifies and decodes a signed JWT."""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            return None
        header_b64, payload_b64, signature_b64 = parts
        signing_input = f"{header_b64}.{payload_b64}".encode("utf-8")

        expected_sig = hmac.new(secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
        actual_sig = base64url_decode(signature_b64)

        if not hmac.compare_digest(expected_sig, actual_sig):
            return None

        payload = json.loads(base64url_decode(payload_b64).decode("utf-8"))
        now = int(time.time())
        if payload.get("exp") and payload["exp"] < now:
            return None  # Expired

        return payload
    except Exception:
        return None
