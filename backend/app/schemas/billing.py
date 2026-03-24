from pydantic import BaseModel


class CheckoutSessionResponse(BaseModel):
    checkout_url: str


class CustomerPortalResponse(BaseModel):
    portal_url: str


class BillingStatusResponse(BaseModel):
    subscription_status: str
    stripe_customer_id: str | None = None
    stripe_subscription_id: str | None = None
    stripe_price_id: str | None = None
    premium_access: bool
