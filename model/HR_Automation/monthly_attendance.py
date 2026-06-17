
from datetime import datetime, date
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Float, ForeignKey, Text
from core.database import Base


class MonthlyAttendanceDay(Base):

    __tablename__ = "monthly_attendance_days"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    att_date    = Column(Date, nullable=False)

    day_code    = Column(String(10), nullable=False, default="A")

    status      = Column(String(50), nullable=False, default="Absent")

    leave_code  = Column(String(20), nullable=True)

    shift_name  = Column(String(100), nullable=True, default="General")

    check_in    = Column(String(20), nullable=True)
    check_out   = Column(String(20), nullable=True)
    worked_hours = Column(Float, default=0.0)

    is_late     = Column(Boolean, default=False)

    has_punch   = Column(Boolean, default=False)

    created_at  = Column(DateTime, default=datetime.utcnow)
    updated_at  = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
