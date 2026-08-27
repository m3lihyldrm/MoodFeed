"""MoodFeed Live Activity, Notifications, and Online Presence Service.

Provides real-time activity feeds, active online community simulation,
and user notification generation.
"""

from __future__ import annotations

import datetime
import random
import time
from typing import Any


SAMPLE_NAMES = [
    ("Ahmet Yılmaz", "ayilmaz", "A"),
    ("Ayşe Kaya", "akaya", "A"),
    ("Mehmet Sever", "msever", "M"),
    ("Zeynep Demir", "zdemir", "Z"),
    ("Burak Çelik", "bcelik", "B"),
    ("Elif Öztürk", "eozturk", "E"),
    ("Caner Aydın", "caydin", "C"),
    ("Selin Koç", "skoc", "S"),
]

SAMPLE_TOPICS = [
    "Yapay Zeka ve Gelecek",
    "Açık Kaynak Geliştirme",
    "Girişimcilik Zirvesi",
    "Web Teknolojileri 2026",
    "Sakin Sosyal Medya Deneyimi",
    "Kültür Sanat Rehberi",
]

ACTION_TEMPLATES = [
    ("{name}, '{topic}' gönderisini beğendi.", "like", "❤️"),
    ("{name}, '{topic}' konusunu paylaştı.", "share", "🔄"),
    ("{name}, {target} kullanıcısını takip etmeye başladı.", "follow", "✨"),
    ("{name}, akışına yeni bir düşünce bıraktı.", "post", "✍️"),
    ("{name}, '{topic}' içeriğini kaydetti.", "save", "🔖"),
]


class ActivityService:
    """Service providing simulated and persistent live interactions."""

    def get_online_users(self) -> dict[str, Any]:
        """Returns online count and active online users list."""
        # Simulated active online count fluctuating slightly
        base_online = 12540
        fluctuation = random.randint(-45, 60)
        online_count = base_online + fluctuation

        active_users = []
        for name, handle, initial in SAMPLE_NAMES:
            active_users.append({
                "name": name,
                "handle": f"@{handle}",
                "avatar": initial,
                "status": "online",
                "last_active": "Şimdi aktif",
            })

        return {
            "online_count": online_count,
            "active_discussions": 4820 + random.randint(-15, 25),
            "users": active_users,
            "summary_text": "Ahmet Y., Ayşe K., Mehmet S. ve 12.5K kişi şu anda çevrimiçi.",
        }

    def get_activity(self, limit: int = 10) -> dict[str, Any]:
        """Returns recent live activity items."""
        now = datetime.datetime.now(datetime.timezone.utc)
        activities = []

        for i in range(limit):
            name, handle, initial = SAMPLE_NAMES[i % len(SAMPLE_NAMES)]
            target_name, _, _ = SAMPLE_NAMES[(i + 2) % len(SAMPLE_NAMES)]
            topic = SAMPLE_TOPICS[i % len(SAMPLE_TOPICS)]
            template, action_type, icon = ACTION_TEMPLATES[i % len(ACTION_TEMPLATES)]

            text = template.format(name=name, topic=topic, target=target_name)
            seconds_ago = (i * 35) + random.randint(5, 20)
            item_time = now - datetime.timedelta(seconds=seconds_ago)

            time_str = "Az önce" if seconds_ago < 60 else f"{seconds_ago // 60} dk önce"

            activities.append({
                "id": f"act-{int(item_time.timestamp())}-{i}",
                "user": name,
                "handle": f"@{handle}",
                "avatar": initial,
                "action": action_type,
                "icon": icon,
                "text": text,
                "topic": topic,
                "time": time_str,
                "timestamp": item_time.isoformat(),
            })

        return {
            "count": len(activities),
            "activities": activities,
            "updated_at": now.isoformat(),
        }

    def get_notifications(self, user_id: str | None = None) -> dict[str, Any]:
        """Returns user notifications."""
        now = datetime.datetime.now(datetime.timezone.utc)
        notifications = [
            {
                "id": "notif-001",
                "type": "like",
                "icon": "❤️",
                "title": "Yeni Beğeni",
                "message": "Ahmet Yılmaz gönderini beğendi.",
                "target": "Girişimcilik ve İnovasyon Zirvesi",
                "time": "2 dk önce",
                "unread": True,
            },
            {
                "id": "notif-002",
                "type": "follow",
                "icon": "✨",
                "title": "Yeni Takipçi",
                "message": "Ayşe Kaya seni takip etmeye başladı.",
                "target": "@akaya",
                "time": "15 dk önce",
                "unread": True,
            },
            {
                "id": "notif-003",
                "type": "comment",
                "icon": "💬",
                "title": "Yeni Yorum",
                "message": "Mehmet Sever gönderine yorum yaptı: 'Harika bir bakış açısı!'",
                "target": "Açık Kaynak Projeleri",
                "time": "1 saat önce",
                "unread": True,
            },
            {
                "id": "notif-004",
                "type": "trend",
                "icon": "📈",
                "title": "Trend Bildirimi",
                "message": "#YapayZeka etiketi bugün %45 daha fazla konuşuluyor.",
                "target": "#YapayZeka",
                "time": "3 saat önce",
                "unread": False,
            },
        ]

        unread_count = sum(1 for n in notifications if n["unread"])

        return {
            "unread_count": unread_count,
            "notifications": notifications,
            "updated_at": now.isoformat(),
        }


activity_service = ActivityService()
