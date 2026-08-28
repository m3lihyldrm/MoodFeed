"""Tests for Stripe Billing, Subscriptions, and Webhook processing."""

from fastapi.testclient import TestClient
from backend.main import app
from backend.services.stripe_service import stripe_service

client = TestClient(app)


def test_get_subscription_plans() -> None:
    res = client.get("/v1/billing/plans")
    assert res.status_code == 200
    data = res.json()
    assert "plans" in data
    assert "free" in data["plans"]
    assert "pro" in data["plans"]
    assert "business" in data["plans"]
    assert data["plans"]["pro"]["price"] == 9


def test_create_checkout_session() -> None:
    payload = {
        "user_id": "00000000-0000-0000-0000-000000000001",
        "user_email": "test@moodfeed.app",
        "plan_id": "pro",
    }
    res = client.post("/v1/billing/checkout", json=payload)
    assert res.status_code == 200
    data = res.json()
    assert "id" in data
    assert "url" in data
    assert data["plan"]["name"] == "Pro"


def test_stripe_webhook_simulation() -> None:
    res = client.post("/v1/webhooks/stripe", json={"type": "test_event"})
    assert res.status_code == 200
    assert res.json()["status"] == "success"
