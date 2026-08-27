"""MoodFeed Session Representation for Auth and Session Management."""

from __future__ import annotations

import datetime
import uuid
from typing import Any


class Session:
    """Represents an active user session."""

    def __init__(
        self,
        user_id: uuid.UUID | str,
        created_at: datetime.datetime | None = None,
    ) -> None:
        if isinstance(user_id, str):
            self.user_id: uuid.UUID = uuid.UUID(user_id)
        else:
            self.user_id = user_id

        self.created_at: datetime.datetime = (
            created_at if created_at is not None else datetime.datetime.now(datetime.timezone.utc)
        )

    def to_dict(self) -> dict[str, Any]:
        """Serializes session to dictionary."""
        return {
            "user_id": str(self.user_id),
            "created_at": (
                self.created_at.isoformat()
                if isinstance(self.created_at, datetime.datetime)
                else str(self.created_at)
            ),
        }
