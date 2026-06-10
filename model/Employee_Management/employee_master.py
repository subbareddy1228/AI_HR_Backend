

from sqlalchemy import Column, Integer, String, Date, DateTime, Numeric, ForeignKey
from core.database import Base
from datetime import datetime


class EmployeeMaster(Base):
    __tablename__ = "employee_master"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False, index=True)
    salary = Column(Numeric(12, 2), nullable=True)          # e.g. 58000.00
    currency = Column(String(10), nullable=False, default="USD")  # USD / INR
    employment_type = Column(String(50), nullable=False, default="Full-Time")
    employment_status = Column(String(50), nullable=False, default="Active")
    probation_end_date = Column(Date, nullable=True)
    confirmed_date = Column(Date, nullable=True)
    notice_period_days = Column(Integer, default=30)
    reporting_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    work_location = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
