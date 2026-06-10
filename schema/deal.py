from pydantic import BaseModel
from typing import Optional
from datetime import date
from enum import Enum as PyEnum



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


class DealBase(BaseModel):
    deal_name: str
    pipeline: Optional[str] = None
    status: Optional[str] = None 
    deal_value: Optional[float] = None
    currency: Optional[str] = None  
    period: Optional[str] = None
    period_value: Optional[int] = None
    contact: Optional[str] = None
    project: Optional[str] = None  
    due_date: Optional[date] = None
    expected_closing_date: Optional[date] = None
    assignee: Optional[str] = None
    tags: Optional[str] = None
    followup_date: Optional[date] = None
    source: Optional[str] = None  
    priority: Optional[str] = None  
    description: Optional[str] = None
    model_config = {"from_attributes": True}




class DealCreate(DealBase):
    pass


class DealUpdate(BaseModel):
    deal_name: Optional[str] = None
    pipeline: Optional[str] = None
    status: Optional[str] = None  
    deal_value: Optional[float] = None
    currency: Optional[str] = None 
    period: Optional[str] = None
    period_value: Optional[int] = None
    contact: Optional[str] = None
    project: Optional[str] = None 
    due_date: Optional[date] = None
    expected_closing_date: Optional[date] = None
    assignee: Optional[str] = None
    tags: Optional[str] = None
    followup_date: Optional[date] = None
    source: Optional[str] = None  
    priority: Optional[str] = None  
    description: Optional[str] = None

    model_config = {"from_attributes": True}


class DealOut(DealBase):
    id: int
    model_config = {"from_attributes": True}
