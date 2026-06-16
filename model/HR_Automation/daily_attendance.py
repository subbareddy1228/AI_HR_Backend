from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, ForeignKey, Text
from core.database import Base


class DailyAttendanceRecord(Base):
    
    __tablename__ = "daily_attendance_records"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    att_date    = Column(Date, nullable=False)

    
    status      = Column(String(50), nullable=False, default="Absent")
    remarks     = Column(Text, nullable=True)   

    
    shift_id    = Column(Integer, ForeignKey("shifts.id", ondelete="SET NULL"), nullable=True)
    shift_name  = Column(String(100), nullable=True, default="General")

    
    check_in        = Column(String(20), nullable=True)   
    check_in_source = Column(String(30), nullable=True)    
    check_out       = Column(String(20), nullable=True)    
    check_out_source = Column(String(30), nullable=True)

    
    worked_hours = Column(Float, default=0.0)

    is_late      = Column(Boolean, default=False)
    is_half_day  = Column(Boolean, default=False)

   
    is_manual    = Column(Boolean, default=False)
    is_uploaded  = Column(Boolean, default=False)

    created_at   = Column(DateTime, default=datetime.utcnow)
    updated_at   = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)