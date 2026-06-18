from sqlalchemy import (
    Column, Integer, String, Date, Boolean, DateTime,
    Text, ForeignKey, Enum as SAEnum
)
from sqlalchemy.orm import relationship
from core.database import Base
from datetime import datetime
import enum



class OptionalAppStatus(str, enum.Enum):
    PENDING  = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"


class CalendarStatus(str, enum.Enum):
    ACTIVE   = "Active"
    INACTIVE = "Inactive"
    DRAFT    = "Draft"


class SwapRequestStatus(str, enum.Enum):
    PENDING  = "Pending"
    APPROVED = "Approved"
    REJECTED = "Rejected"
    CANCELLED = "Cancelled"


class CarryForwardStatus(str, enum.Enum):
    PENDING    = "Pending"
    PROCESSED  = "Processed"
    FAILED     = "Failed"





class Holiday(Base):
    __tablename__ = "holidays"

    id = Column(Integer, primary_key=True, index=True)
    holiday_name = Column(String(255), nullable=False)
    holiday_date = Column(Date, nullable=False)
    holiday_type = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True)




class OptionalHolidayApplication(Base):
    
    __tablename__ = "optional_holiday_applications"

    id            = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(Integer, ForeignKey("employee_master.id"), nullable=False, index=True)
    holiday_id    = Column(Integer, ForeignKey("holidays.id"), nullable=False)
    holiday_name  = Column(String(255), nullable=True)   
    holiday_date  = Column(Date, nullable=False)
    applied_on    = Column(DateTime, default=datetime.utcnow)
    status        = Column(SAEnum(OptionalAppStatus), default=OptionalAppStatus.PENDING)
    reason        = Column(Text, nullable=True)
    approved_by   = Column(Integer, nullable=True)        
    approved_on   = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class HolidayCalendar(Base):
   
    __tablename__ = "holiday_calendars"

    id              = Column(Integer, primary_key=True, index=True)
    calendar_name   = Column(String(255), nullable=False)
    location        = Column(String(150), nullable=True)   
    employee_groups = Column(String(255), nullable=True)   
    status          = Column(SAEnum(CalendarStatus), default=CalendarStatus.ACTIVE)
    is_default      = Column(Boolean, default=False)       
    description     = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    holiday_links = relationship(
        "HolidayCalendarMapping",
        back_populates="calendar",
        cascade="all, delete-orphan",
    )


class HolidayCalendarMapping(Base):
    
    __tablename__ = "holiday_calendar_mappings"

    id          = Column(Integer, primary_key=True, index=True)
    calendar_id = Column(Integer, ForeignKey("holiday_calendars.id"), nullable=False)
    holiday_id  = Column(Integer, ForeignKey("holidays.id"), nullable=False)
    created_at  = Column(DateTime, default=datetime.utcnow)

    calendar = relationship("HolidayCalendar", back_populates="holiday_links")



class HolidaySwapRequest(Base):
  
    __tablename__ = "holiday_swap_requests"

    id           = Column(Integer, primary_key=True, index=True)
    employee_id  = Column(Integer, ForeignKey("employee_master.id"), nullable=False, index=True)
    holiday_id   = Column(Integer, ForeignKey("holidays.id"), nullable=True)
    holiday_date = Column(Date, nullable=False)     
    work_date    = Column(Date, nullable=False)     
    reason       = Column(Text, nullable=True)
    status       = Column(SAEnum(SwapRequestStatus), default=SwapRequestStatus.PENDING)
    approved_by  = Column(Integer, nullable=True)
    approved_on  = Column(DateTime, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)




class HolidayCarryForward(Base):
    
    __tablename__ = "holiday_carry_forwards"

    id            = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(Integer, ForeignKey("employee_master.id"), nullable=False, index=True)
    from_year     = Column(Integer, nullable=False)
    to_year       = Column(Integer, nullable=False)
    holidays_count = Column(Integer, default=0)       
    status        = Column(SAEnum(CarryForwardStatus), default=CarryForwardStatus.PENDING)
    processed_by  = Column(Integer, nullable=True)    
    processed_on  = Column(DateTime, nullable=True)
    remarks       = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


