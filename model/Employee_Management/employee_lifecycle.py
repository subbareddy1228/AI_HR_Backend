# model/Employee_Management/employee_lifecycle.py

from sqlalchemy import Column, Integer, String, Date, DateTime, Text, ForeignKey
from core.database import Base
from datetime import datetime


class EmployeeLifecycleEvent(Base):
    """
    One row per lifecycle stage transition.
    Covers: JOINING → PROBATION → CONFIRMED → TRANSFER → PROMOTION → EXIT

    Every stage creates a new row here — this is the single source of truth
    for an employee's full career history inside the company.
    """
    __tablename__ = "employee_lifecycle_events"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(
        Integer,
        ForeignKey("employees.id"),
        nullable=False,
        index=True,
    )

  
    stage = Column(String(50), nullable=False)
    status = Column(String(50), nullable=False, default="PENDING")

    effective_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=True)        
    from_value = Column(String(255), nullable=True)
    to_value = Column(String(255), nullable=True)
    sub_type = Column(String(100), nullable=True)

    remarks = Column(Text, nullable=True)

    initiated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
