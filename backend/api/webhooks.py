"""MoodFeed Billing, Stripe Checkout & Webhook API Router."""

from __future__ import annotations

from typing import Any
from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel
from backend.services.stripe_service import stripe_service

router = APIRouter(tags=["billing"])


class CreateCheckoutRequest(BaseModel):
    user_id: str
    user_email: str
    plan_id: str


@router.get("/v1/billing/plans")
@router.get("/billing/plans")
def get_subscription_plans() -> dict[str, Any]:
    """Returns available SaaS pricing tiers (Free, Pro, Business)."""
    return {"plans": stripe_service.get_plans()}


@router.post("/v1/billing/checkout")
@router.post("/billing/checkout")
def create_checkout_session(payload: CreateCheckoutRequest) -> dict[str, Any]:
    """Initiates Stripe Checkout session for subscription upgrade."""
    return stripe_service.create_checkout_session(
        user_id=payload.user_id,
        user_email=payload.user_email,
        plan_id=payload.plan_id,
    )


@router.post("/v1/webhooks/stripe")
async def stripe_webhook_endpoint(
    request: Request,
    stripe_signature: str | None = Header(None, alias="stripe-signature"),
) -> dict[str, Any]:
    """Stripe webhook receiver for invoice & subscription events."""
    payload = await request.body()
    result = stripe_service.handle_webhook(payload, stripe_signature)
    if result.get("status") == "error":
        raise HTTPException(status_code=400, detail=result.get("detail"))
    return result
