from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from core.database import get_db
from schema.billing.subscription import SubscriptionCreate, SubscriptionResponse
from services.billing_service import create_subscription, list_subscriptions_for_email

router = APIRouter(prefix="/subscriptions", tags=["Billing"])


@router.post("/", response_model=SubscriptionResponse)
def submit_subscription(payload: SubscriptionCreate, db: Session = Depends(get_db)):
    """
    Records the plan a user selected on the Pricing page.
    NOTE: no payment gateway is integrated yet — this does not charge any
    money. Every record is created with status='pending_payment'. Wire a
    real gateway (e.g. Razorpay/Stripe) before treating this as billing.
    """
    return create_subscription(db, payload)


@router.get("/by-email/{email}", response_model=list[SubscriptionResponse])
def get_subscriptions_for_email(email: str, db: Session = Depends(get_db)):
    return list_subscriptions_for_email(db, email)