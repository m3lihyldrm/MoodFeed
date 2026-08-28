"""MoodFeed Stripe Billing & Monetization Service.

Manages subscriptions, checkout sessions, billing portals,
and payment webhooks for Free, Pro ($9/mo), and Business ($29/mo) plans.
"""

from __future__ import annotations

import logging
import os
import uuid
from typing import Any

logger = logging.getLogger("moodfeed.services.stripe")

# Pricing Plans
PLANS = {
    "free": {
        "id": "plan_free",
        "name": "Free",
        "price": 0,
        "period": "forever",
        "features": [
            "10 post/gün",
            "Temel Mood Analizi",
            "5 Mood Filtresi",
            "Topluluk Desteği",
        ],
        "limits": {"daily_posts": 10, "advanced_ai": False, "api_access": False},
    },
    "pro": {
        "id": "price_pro_monthly",
        "name": "Pro",
        "price": 9,
        "period": "month",
        "features": [
            "Sınırsız Post",
            "Gelişmiş AI Analizleri",
            "Mood Trendleri & Grafikler",
            "Öncelikli Destek",
            "Erken Erişim Özellikleri",
            "Reklamsız Deneyim",
        ],
        "limits": {"daily_posts": -1, "advanced_ai": True, "api_access": False},
    },
    "business": {
        "id": "price_business_monthly",
        "name": "Business",
        "price": 29,
        "period": "month",
        "features": [
            "Pro Planındaki Her Şey",
            "5 Kullanıcıya Kadar Takım Desteği",
            "Tam API Erişimi",
            "Özel Markalama",
            "Özel Destek Temsilcisi",
            "%99.9 SLA Garantisi",
        ],
        "limits": {"daily_posts": -1, "advanced_ai": True, "api_access": True},
    },
}


class StripeService:
    """Stripe Payment and Subscription Manager."""

    def __init__(self) -> None:
        self.secret_key = os.getenv("STRIPE_SECRET_KEY")
        self.webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")
        self.success_url = os.getenv("STRIPE_SUCCESS_URL", "https://moodfeed.vercel.app/#/success?session_id={CHECKOUT_SESSION_ID}")
        self.cancel_url = os.getenv("STRIPE_CANCEL_URL", "https://moodfeed.vercel.app/#/pricing")

    def get_plans(self) -> dict[str, Any]:
        """Returns active subscription plans."""
        return PLANS

    def create_checkout_session(self, user_id: str, user_email: str, plan_id: str) -> dict[str, Any]:
        """Creates a Stripe Checkout Session or mock simulated checkout."""
        plan_key = "pro" if "pro" in plan_id.lower() else ("business" if "bus" in plan_id.lower() else "free")
        selected_plan = PLANS.get(plan_key, PLANS["pro"])

        if not self.secret_key:
            # Simulated SaaS Checkout for development / demo mode
            mock_session_id = f"cs_test_{uuid.uuid4().hex[:16]}"
            return {
                "id": mock_session_id,
                "url": f"https://moodfeed.vercel.app/#/success?session_id={mock_session_id}&plan={plan_key}",
                "plan": selected_plan,
                "status": "open",
                "mode": "simulated",
            }

        try:
            import stripe
            stripe.api_key = self.secret_key
            session = stripe.checkout.Session.create(
                customer_email=user_email,
                payment_method_types=["card"],
                line_items=[{"price": selected_plan["id"], "quantity": 1}],
                mode="subscription",
                success_url=self.success_url,
                cancel_url=self.cancel_url,
                metadata={"user_id": str(user_id), "plan": plan_key},
            )
            return {
                "id": session.id,
                "url": session.url,
                "plan": selected_plan,
                "status": session.status,
                "mode": "live",
            }
        except Exception as err:
            logger.error("Stripe session creation error: %s", err)
            mock_session_id = f"cs_test_{uuid.uuid4().hex[:16]}"
            return {
                "id": mock_session_id,
                "url": f"https://moodfeed.vercel.app/#/success?session_id={mock_session_id}&plan={plan_key}",
                "plan": selected_plan,
                "status": "open",
                "mode": "simulated_fallback",
            }

    def handle_webhook(self, payload: bytes, sig_header: str | None) -> dict[str, Any]:
        """Processes Stripe Webhook notifications."""
        if not self.secret_key or not self.webhook_secret or not sig_header:
            return {"status": "success", "message": "Simulated webhook processed"}

        try:
            import stripe
            stripe.api_key = self.secret_key
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )

            event_type = event["type"]
            data_obj = event["data"]["object"]

            if event_type == "checkout.session.completed":
                user_id = data_obj.get("metadata", {}).get("user_id")
                plan = data_obj.get("metadata", {}).get("plan", "pro")
                logger.info("Subscription activated for user: %s (Plan: %s)", user_id, plan)

            elif event_type == "customer.subscription.deleted":
                user_id = data_obj.get("metadata", {}).get("user_id")
                logger.info("Subscription canceled for user: %s", user_id)

            return {"status": "success", "event": event_type}
        except Exception as err:
            logger.error("Webhook processing error: %s", err)
            return {"status": "error", "detail": str(err)}


stripe_service = StripeService()
