from sqlalchemy.orm import Session

from model.billing.subscription import Subscription
from schema.billing.subscription import SubscriptionCreate


def create_subscription(db: Session, data: SubscriptionCreate) -> Subscription:
    sub = Subscription(
        email=data.email,
        plan_name=data.plan_name,
        billing_cycle=data.billing_cycle,
        address_line=data.address_line,
        city=data.city,
        state=data.state,
        zip_code=data.zip_code,
        country=data.country,
        payment_method=data.payment_method,
        subtotal=data.subtotal,
        tax_rate=data.tax_rate,
        tax_amount=data.tax_amount,
        total_amount=data.total_amount,
        currency=data.currency,
        # No payment gateway is integrated — every subscription starts
        # "pending_payment" rather than being marked active/paid.
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def list_subscriptions_for_email(db: Session, email: str):
    return db.query(Subscription).filter(Subscription.email == email).order_by(Subscription.created_at.desc()).all()