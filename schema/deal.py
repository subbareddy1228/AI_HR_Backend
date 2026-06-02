from pydantic import BaseModel
from typing import Optional
from datetime import date
from enum import Enum as PyEnum



# ENUMS (match frontend)
class DealStatus(str, PyEnum):
    OPEN = "Open"
    WON = "Won"
    LOST = "Lost"

class DealCurrency(str, PyEnum):
    RUPEE = "Rupee"
    DOLLAR = "Dollar"
    EURO = "Euro"

class DealSource(str, PyEnum):
    PHONE_CALLS = "Phone Calls"
    SOCIAL_MEDIA = "Social Media"
    REFERRAL_SITES = "Referral Sites"
    WEB_ANALYTICS = "Web Analytics"
    PREVIOUS_PURCHASE = "Previous Purchase"

class DealPriority(str, PyEnum):
    HIGH = "High"
    LOW = "Low"
    MEDIUM = "Medium"

class DealProject(str, PyEnum):
    OFFICE_MANAGEMENT = "Office Management App"
    CLINIC_MANAGEMENT = "Clinic Management"
    EDUCATIONAL_PLATFORM = "Educational Platform"



# BASE SCHEMA
class DealBase(BaseModel):
    deal_name: str
    pipeline: Optional[str] = None
    status: Optional[str] = None  # Changed from DealStatus enum to str to accept stage values (New, Prospect, Proposal, Won, Open, Lost)
    deal_value: Optional[float] = None
    currency: Optional[str] = None  # Changed from DealCurrency enum to str to be more flexible
    period: Optional[str] = None
    period_value: Optional[int] = None
    contact: Optional[str] = None
    project: Optional[str] = None  # Changed from DealProject enum to str to be more flexible
    due_date: Optional[date] = None
    expected_closing_date: Optional[date] = None
    assignee: Optional[str] = None
    tags: Optional[str] = None
    followup_date: Optional[date] = None
    source: Optional[str] = None  # Changed from DealSource enum to str to be more flexible
    priority: Optional[str] = None  # Changed from DealPriority enum to str to be more flexible
    description: Optional[str] = None
    model_config = {"from_attributes": True}



# CREATE SCHEMA
class DealCreate(DealBase):
    pass

# UPDATE SCHEMA
class DealUpdate(BaseModel):
    deal_name: Optional[str] = None
    pipeline: Optional[str] = None
    status: Optional[str] = None  # Changed from DealStatus enum to str
    deal_value: Optional[float] = None
    currency: Optional[str] = None  # Changed from DealCurrency enum to str
    period: Optional[str] = None
    period_value: Optional[int] = None
    contact: Optional[str] = None
    project: Optional[str] = None  # Changed from DealProject enum to str
    due_date: Optional[date] = None
    expected_closing_date: Optional[date] = None
    assignee: Optional[str] = None
    tags: Optional[str] = None
    followup_date: Optional[date] = None
    source: Optional[str] = None  # Changed from DealSource enum to str
    priority: Optional[str] = None  # Changed from DealPriority enum to str
    description: Optional[str] = None

    model_config = {"from_attributes": True}

# OUTPUT SCHEMA
class DealOut(DealBase):
    id: int
    model_config = {"from_attributes": True}
