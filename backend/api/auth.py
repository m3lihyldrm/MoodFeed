"""MoodFeed Authentication API Endpoints.

Provides registration, login, logout, and current user profile endpoints.
"""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from backend.config import settings
from backend.db.database import get_db
from backend.services.auth_service import auth_service_instance

router = APIRouter(tags=["auth"])


@router.get("/v1/auth/config")
@router.get("/auth/config")
def get_auth_config() -> dict[str, Any]:
    """Returns public authentication configuration for frontend runtime."""
    is_clerk = bool(
        settings.auth_provider == "clerk"
        and settings.feature_flag_clerk_auth
        and settings.clerk_publishable_key
    )
    provider = "clerk" if is_clerk else (settings.auth_provider if settings.feature_flag_auth else "local")
    return {
        "auth_provider": "clerk" if is_clerk else provider,
        "clerk_publishable_key": settings.clerk_publishable_key if is_clerk else None,
        "features": {
            "clerk_auth": is_clerk,
            "local_auth_fallback": False if is_clerk else bool(settings.feature_flag_mock_adapter),
        },
    }


class RegisterRequest(BaseModel):
    email: str = Field(..., description="E-posta adresi")
    password: str = Field(..., min_length=6, description="Şifre")
    username: str | None = Field(None, description="Kullanıcı adı")
    display_name: str | None = Field(None, description="Görünen isim")


class LoginRequest(BaseModel):
    email: str = Field(..., description="E-posta veya kullanıcı adı")
    password: str = Field(..., description="Şifre")


def get_current_user_from_header(authorization: str | None = Header(None), db: Session = Depends(get_db)) -> dict[str, Any]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Geçerli bir oturum token'ı gereklidir."},
        )
    token = authorization.split(" ")[1]
    user = auth_service_instance.get_current_user_from_token(token, db=db)
    if not user:
        raise HTTPException(
            status_code=401,
            detail={"code": "UNAUTHORIZED", "message": "Oturum süresi dolmuş veya geçersiz."},
        )
    return user


@router.post("/v1/register")
@router.post("/register")
def register_user(payload: RegisterRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Kayıt sayfası endpoint'i."""
    try:
        return auth_service_instance.register(
            email=payload.email,
            password=payload.password,
            username=payload.username,
            display_name=payload.display_name,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=400,
            detail={"code": "REGISTRATION_FAILED", "message": str(e)},
        )


@router.post("/v1/login")
@router.post("/login")
def login_user(payload: LoginRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Giriş sayfası endpoint'i."""
    try:
        return auth_service_instance.login(
            email=payload.email,
            password=payload.password,
            db=db,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=401,
            detail={"code": "AUTHENTICATION_FAILED", "message": str(e)},
        )


@router.post("/v1/logout")
@router.post("/logout")
def logout_user() -> dict[str, Any]:
    """Çıkış endpoint'i."""
    return {"success": True, "message": "Çıkış başarılı."}


@router.get("/v1/me")
@router.get("/me")
def get_current_user(user: dict[str, Any] = Depends(get_current_user_from_header)) -> dict[str, Any]:
    """Aktif kullanıcı profili."""
    return user


class ClerkSyncRequest(BaseModel):
    clerk_id: str = Field(..., description="Clerk User ID")
    email: str = Field(..., description="E-posta adresi")
    username: str | None = Field(None, description="Kullanıcı adı")
    display_name: str | None = Field(None, description="Görünen isim")
    avatar: str | None = Field(None, description="Avatar URL veya simge")


@router.post("/v1/auth/clerk-sync")
@router.post("/auth/clerk-sync")
def sync_clerk_user(payload: ClerkSyncRequest, db: Session = Depends(get_db)) -> dict[str, Any]:
    """Clerk ile oturum açmış kullanıcıyı yerel SQLite veritabanına senkronize eder."""
    from backend.auth.clerk import get_or_sync_clerk_user
    claims = {
        "sub": payload.clerk_id,
        "email": payload.email,
        "username": payload.username,
        "display_name": payload.display_name,
        "avatar": payload.avatar,
    }
    user_dict = get_or_sync_clerk_user(claims, db=db)
    return {
        "success": True,
        "message": "Kullanıcı başarıyla senkronize edildi.",
        "user": user_dict,
    }
