from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, ForeignKey, Text
from core.database import Base


class DailyPunchSummary(Base):
    __tablename__ = "daily_punch_summaries"

    id            = Column(Integer, primary_key=True, index=True)
    employee_id   = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    summary_date  = Column(Date, nullable=False)

    in_time       = Column(String(20), nullable=True)    
    out_time      = Column(String(20), nullable=True)    
    duration      = Column(String(20), default="0h 0m") 

    attendance_mark = Column(String(50), default="Absent")  
    is_late         = Column(Boolean, default=False)
    process_status  = Column(String(20), default="Pending")  

    regularised    = Column(Boolean, default=False)
    regularise_reason = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)