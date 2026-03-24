from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from app.api.dependencies.auth import get_current_active_user
from app.db.session import get_db_session
from app.models.user import User
from app.schemas.billing import BillingStatusResponse, CheckoutSessionResponse, CustomerPortalResponse
from app.services.billing import BillingService

router = APIRouter()


@router.get("", response_model=BillingStatusResponse)
def get_billing_status(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> BillingStatusResponse:
    return BillingService(session).get_billing_status(current_user)


@router.post("/checkout", response_model=CheckoutSessionResponse)
def create_checkout_session(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> CheckoutSessionResponse:
    return CheckoutSessionResponse(checkout_url=BillingService(session).create_checkout_session(current_user))


@router.post("/portal", response_model=CustomerPortalResponse)
def create_customer_portal_session(
    current_user: User = Depends(get_current_active_user),
    session: Session = Depends(get_db_session),
) -> CustomerPortalResponse:
    return CustomerPortalResponse(portal_url=BillingService(session).create_portal_session(current_user))


@router.post("/webhook", include_in_schema=False)
async def stripe_webhook(
    request: Request,
    session: Session = Depends(get_db_session),
) -> dict[str, str]:
    payload = await request.body()
    BillingService(session).handle_webhook(payload, request.headers.get("stripe-signature"))
    return {"status": "ok"}
