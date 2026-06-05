from pydantic import BaseModel
from datetime import datetime, date
from typing import Optional
 
 
class AttendanceUpdate(BaseModel):
    login_time: Optional[datetime] = None
    logout_time: Optional[datetime] = None
    status: Optional[str] = None
 
 
class AttendanceResponse(BaseModel):
    id: int
    date: date
    login_time: Optional[datetime]
    logout_time: Optional[datetime]
    total_hours: str
    status: str
 
    class Config:
        from_attributes = True