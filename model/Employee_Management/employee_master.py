# FILE 1 of 12 | model/Employee_Management/employee_master.py
# Model: EmployeeMaster — extra HR profile data linked to Employee
# Table: employee_master

from sqlalchemy import Column, Integer, String, Date, DateTime, ForeignKey
from core.database import Base
from datetime import datetime


class EmployeeMaster(Base):
    __tablename__ = "employee_master"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), unique=True, nullable=False)
    employment_type = Column(String(50), nullable=False)  # Full-Time/Part-Time/Contract/Intern
    probation_end_date = Column(Date, nullable=True)
    confirmed_date = Column(Date, nullable=True)
    reporting_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    work_location = Column(String(255), nullable=True)
    employment_status = Column(String(50), nullable=False, default="Active")  # Active/Inactive/On Leave/Resigned/Terminated
    notice_period_days = Column(Integer, default=30)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
