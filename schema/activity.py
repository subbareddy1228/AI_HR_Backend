from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import date, datetime, time
from enum import Enum as PyEnum

from datetime import date, time
from pydantic import BaseModel
from typing import Optional


class ActivityBase(BaseModel):
    title: str
    activity_type: str
    due_date: Optional[date] = None
    activity_time: Optional[time] = None
    remainder: Optional[str] = None
    remainder_type: Optional[str] = None
    owner: Optional[str] = None
    guests: Optional[str] = None       
    description: Optional[str] = None
    deals: Optional[str] = None        
    contacts: Optional[str] = None     
    companies: Optional[str] = None    
    created_date: Optional[date] = None

# Schema for creating an activity
class ActivityCreate(ActivityBase):
    pass

# Schema for updating an activity
class ActivityUpdate(ActivityBase):
    pass

# Schema for returning an activity (with ID)
class Activity(ActivityBase):
    id: int

    class Config:
        orm_mode = True  
