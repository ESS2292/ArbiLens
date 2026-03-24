from datetime import UTC, datetime

import stripe
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import AppError
from app.models.organization import Organization
from app.models.user import User
from app.schemas.billing import BillingStatusResponse


def organization_has_premium_access(organization: Organization) -> bool:
    return organization.stripe_subscription_status in {"active", "trialing"}


class BillingService:
    def __init__(self, session: Session) -> None:
        self.session = session
        self.settings = get_settings()
        stripe.api_key = self.settings.stripe_secret_key

    def get_billing_status(self, current_user: User) -> BillingStatusResponse:
        organization = current_user.organization
        return BillingStatusResponse(
            subscription_status=organization.stripe_subscription_status,
            stripe_customer_id=organization.stripe_customer_id,
            stripe_subscription_id=organization.stripe_subscription_id,
            stripe_price_id=organization.stripe_price_id,
            premium_access=organization_has_premium_access(organization),
        )

    def create_checkout_session(self, current_user: User) -> str:
        if not self.settings.stripe_price_id:
            raise AppError("Stripe pricing is not configured.", status_code=503, code="billing_not_configured")
        organization = current_user.organization
        customer_id = organization.stripe_customer_id or self._ensure_customer(organization, current_user)
        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=customer_id,
            line_items=[{"price": self.settings.stripe_price_id, "quantity": 1}],
            success_url=f"{self.settings.app_base_url}/billing?checkout=success",
            cancel_url=f"{self.settings.app_base_url}/billing?checkout=cancelled",
        )
        if not session.url:
            raise AppError("Stripe checkout URL is missing.", status_code=502, code="stripe_checkout_failed")
        return session.url

    def create_portal_session(self, current_user: User) -> str:
        organization = current_user.organization
        if not organization.stripe_customer_id:
            raise AppError("Stripe customer is not configured.", status_code=409, code="billing_not_ready")
        session = stripe.billing_portal.Session.create(
            customer=organization.stripe_customer_id,
            return_url=f"{self.settings.app_base_url}/billing",
        )
        return session.url

    def handle_webhook(self, payload: bytes, signature: str | None) -> None:
        if not self.settings.stripe_webhook_secret:
            raise AppError("Stripe webhook secret is not configured.", status_code=503, code="billing_not_configured")
        if signature is None:
            raise AppError("Missing Stripe signature.", status_code=400, code="missing_stripe_signature")
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=signature,
                secret=self.settings.stripe_webhook_secret,
            )
        except ValueError as exc:
            raise AppError("Invalid Stripe payload.", status_code=400, code="invalid_stripe_payload") from exc
        except stripe.error.SignatureVerificationError as exc:
            raise AppError("Invalid Stripe signature.", status_code=400, code="invalid_stripe_signature") from exc

        event_type = event["type"]
        data_object = event["data"]["object"]
        if event_type == "checkout.session.completed":
            customer_id = data_object.get("customer")
            subscription_id = data_object.get("subscription")
            if customer_id:
                organization = self.session.query(Organization).filter_by(stripe_customer_id=customer_id).one_or_none()
                if organization:
                    organization.stripe_subscription_id = subscription_id
                    organization.stripe_subscription_status = "active"
                    organization.stripe_price_id = self.settings.stripe_price_id
                    self.session.commit()
        elif event_type == "customer.subscription.updated":
            self._sync_subscription(data_object)
        elif event_type == "customer.subscription.deleted":
            self._sync_subscription(data_object, deleted=True)

    def _sync_subscription(self, subscription, deleted: bool = False) -> None:
        organization = (
            self.session.query(Organization)
            .filter_by(stripe_customer_id=subscription.get("customer"))
            .one_or_none()
        )
        if organization is None:
            return
        organization.stripe_subscription_id = None if deleted else subscription.get("id")
        organization.stripe_subscription_status = "inactive" if deleted else subscription.get("status", "inactive")
        period_end = subscription.get("current_period_end")
        organization.subscription_current_period_end = (
            datetime.fromtimestamp(period_end, UTC) if period_end else None
        )
        items = subscription.get("items", {}).get("data", [])
        organization.stripe_price_id = items[0]["price"]["id"] if items else organization.stripe_price_id
        self.session.commit()

    def _ensure_customer(self, organization: Organization, user: User) -> str:
        customer = stripe.Customer.create(
            name=organization.name,
            email=user.email,
            metadata={"organization_id": str(organization.id)},
        )
        organization.stripe_customer_id = customer.id
        self.session.commit()
        return customer.id
