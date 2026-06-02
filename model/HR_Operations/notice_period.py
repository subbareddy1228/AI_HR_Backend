from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey
from core.database import Base
from datetime import datetime


class NoticePeriod(Base):
    __tablename__ = "notice_periods"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    notice_start_date = Column(Date, nullable=False)
    notice_end_date = Column(Date, nullable=False)
    notice_period_days = Column(Integer, nullable=False)    # contractual notice days
    serving_days = Column(Integer, nullable=True)           # actual days served
    waiver_requested = Column(String(10), nullable=False, server_default="NO")   # YES | NO
    waiver_approved = Column(String(10), nullable=False, server_default="NO")    # YES | NO
    buyout_amount = Column(Integer, nullable=True)          # if notice is bought out
    status = Column(String(50), nullable=False, server_default="SERVING")  # SERVING | COMPLETED | WAIVED | BUYOUT
    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
