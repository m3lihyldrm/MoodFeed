"""MoodFeed User Interactions API.

Handles user actions (like, save, hide, less_like_this, mute_source) with SQLite/PostgreSQL persistence.
"""

from __future__ import annotations

import logging
from typing import Any
from fastapi import APIRouter, Depends, Header, HTTPException, Query
from sqlalchemy.orm import Session

from backend.auth.security import verify_jwt_token
from backend.config import settings
from backend.database.repository import get_interactions_from_db, save_interaction_to_db
from backend.db.database import get_db
from backend.models import UserActionCreate, UserActionRead, UserActionResponse

logger = logging.getLogger("moodfeed.api.interactions")
router = APIRouter(prefix="/v1/interactions", tags=["interactions"])


def resolve_user_id(authorization: str | None = None, payload_user_id: str | None = None) -> str:
    """Extracts user ID from authorization token if present, otherwise uses payload ID or default guest ID."""
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split("Bearer ", 1)[1].strip()
        payload = verify_jwt_token(token, settings.jwt_secret)
        if payload and payload.get("sub"):
            return str(payload["sub"])
    if payload_user_id and payload_user_id.strip():
        return payload_user_id.strip()
    return "00000000-0000-0000-0000-000000000001"


@router.post("", response_model=UserActionResponse)
def record_user_action(
    payload: UserActionCreate,
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> UserActionResponse:
    """Records a user action (like, save, hide, less_like_this, mute_source) to database."""
    user_id = resolve_user_id(authorization=authorization, payload_user_id=payload.user_id)

    action_record = save_interaction_to_db(
        user_id=user_id,
        content_id=payload.content_id,
        action_type=payload.action_type,
        source=payload.source,
        category=payload.category,
        extra_data=payload.extra_data,
        db=db,
    )

    action_read = UserActionRead(
        id=str(action_record.get("id")),
        user_id=str(action_record.get("user_id")),
        content_id=str(action_record.get("content_id")),
        action_type=str(action_record.get("action_type")),
        source=action_record.get("source"),
        category=action_record.get("category"),
        created_at=str(action_record.get("created_at")),
    )

    action_labels = {
        "like": "İçerik beğenildi.",
        "unlike": "Beğeni kaldırıldı.",
        "save": "İçerik kaydedildi.",
        "unsave": "Kayıt kaldırıldı.",
        "hide": "İçerik gizlendi.",
        "less_like_this": "Bu tür içerikler daha az gösterilecek.",
        "mute_source": f"'{payload.source or 'Kaynak'}' kaynağı sessize alındı.",
        "unmute_source": f"'{payload.source or 'Kaynak'}' kaynağının sesi açıldı.",
    }
    msg = action_labels.get(payload.action_type, f"'{payload.action_type}' aksiyonu kaydedildi.")

    return UserActionResponse(
        success=True,
        message=msg,
        action=action_read,
    )


@router.get("", response_model=list[UserActionRead])
def list_user_actions(
    user_id: str | None = Query(None, description="Kullanıcı ID'si"),
    action_type: str | None = Query(None, description="Filtrelenecek aksiyon türü"),
    limit: int = Query(50, ge=1, le=200, description="Kayıt limiti"),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> list[UserActionRead]:
    """Retrieves user's past interaction history."""
    effective_user_id = resolve_user_id(authorization=authorization, payload_user_id=user_id)
    items = get_interactions_from_db(
        user_id=effective_user_id,
        action_type=action_type,
        limit=limit,
        db=db,
    )

    return [
        UserActionRead(
            id=str(item.get("id")),
            user_id=str(item.get("user_id")),
            content_id=str(item.get("content_id")),
            action_type=str(item.get("action_type")),
            source=item.get("source"),
            category=item.get("category"),
            created_at=str(item.get("created_at")),
        )
        for item in items
    ]


@router.get("/summary")
def get_user_interaction_summary(
    user_id: str | None = Query(None),
    authorization: str | None = Header(None),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Returns summarized sets of user interactions for client personalization."""
    effective_user_id = resolve_user_id(authorization=authorization, payload_user_id=user_id)
    items = get_interactions_from_db(user_id=effective_user_id, limit=200, db=db)

    liked_ids: set[str] = set()
    saved_ids: set[str] = set()
    hidden_ids: set[str] = set()
    less_like_ids: set[str] = set()
    muted_sources: set[str] = set()

    for item in items:
        act = item.get("action_type")
        cid = item.get("content_id")
        src = item.get("source")

        if act == "like" and cid:
            liked_ids.add(cid)
        elif act == "unlike" and cid:
            liked_ids.discard(cid)
        elif act == "save" and cid:
            saved_ids.add(cid)
        elif act == "unsave" and cid:
            saved_ids.discard(cid)
        elif act == "hide" and cid:
            hidden_ids.add(cid)
        elif act == "less_like_this" and cid:
            less_like_ids.add(cid)
        elif act == "mute_source" and src:
            muted_sources.add(src)
        elif act == "unmute_source" and src:
            muted_sources.discard(src)

    return {
        "user_id": effective_user_id,
        "liked_content_ids": list(liked_ids),
        "saved_content_ids": list(saved_ids),
        "hidden_content_ids": list(hidden_ids),
        "less_like_content_ids": list(less_like_ids),
        "muted_sources": list(muted_sources),
    }
