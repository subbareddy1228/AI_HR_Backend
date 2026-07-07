from sqlalchemy import Column, Integer, String, Float, DateTime, Enum
from datetime import datetime
from core.database import Base
import enum


class BillingCycleEnum(enum.Enum):
    monthly = "monthly"
    yearly = "yearly"


class SubscriptionStatusEnum(enum.Enum):
    # No real payment gateway is wired up yet — every subscription created
    # through this endpoint is recorded as "pending_payment" so it's obvious
    # in the data that no money has actually changed hands.
    pending_payment = "pending_payment"
    active = "active"
    cancelled = "cancelled"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(150), nullable=False, index=True)

    plan_name = Column(String(50), nullable=False)
    billing_cycle = Column(Enum(BillingCycleEnum), nullable=False)

    address_line = Column(String(255), nullable=True)
    city = Column(String(100), nullable=True)
    state = Column(String(100), nullable=True)
    zip_code = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)

    payment_method = Column(String(20), nullable=True)  # 'card' | 'upi' (not actually charged)

    subtotal = Column(Float, nullable=False, default=0)
    tax_rate = Column(Float, nullable=False, default=0)
    tax_amount = Column(Float, nullable=False, default=0)
    total_amount = Column(Float, nullable=False, default=0)
    currency = Column(String(10), nullable=False, default="INR")

    status = Column(Enum(SubscriptionStatusEnum), nullable=False, default=SubscriptionStatusEnum.pending_payment)
    created_at = Column(DateTime, default=datetime.utcnow)