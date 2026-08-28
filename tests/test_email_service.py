"""Tests for Email Service dispatch and formatting."""

from backend.services.email_service import email_service


def test_email_service_welcome_dispatch() -> None:
    success = email_service.send_welcome_email("test@moodfeed.app", "Test User")
    assert success is True


def test_email_service_weekly_digest() -> None:
    stats = {"posts": 5, "likes": 42, "followers": 10, "avg_mood": "😊 Mutlu"}
    success = email_service.send_weekly_digest("test@moodfeed.app", "Test User", stats)
    assert success is True


def test_email_service_password_reset() -> None:
    success = email_service.send_password_reset("test@moodfeed.app", "reset_token_xyz123")
    assert success is True
