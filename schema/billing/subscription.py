from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr


class SubscriptionCreate(BaseModel):
    email: EmailStr
    plan_name: str
    billing_cycle: str  # 'monthly' | 'yearly'

    address_line: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip_code: Optional[str] = None
    country: Optional[str] = None

    payment_method: Optional[str] = None  # 'card' | 'upi' — recorded only, never charged

    subtotal: float
    tax_rate: float = 0
    tax_amount: float = 0
    total_amount: float
    currency: str = "INR"


class SubscriptionResponse(SubscriptionCreate):
    id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True