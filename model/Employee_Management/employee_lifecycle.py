# model/Employee_Management/employee_lifecycle.py

from sqlalchemy import Column, Integer, String, Date, Text, DateTime, Boolean, ForeignKey
from datetime import datetime
from core.database import Base


class EmployeeLifecycleEvent(Base):
    __tablename__ = "employee_lifecycle_events"

    id = Column(Integer, primary_key=True, index=True)

    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)
    event_type = Column(String(100), nullable=False, index=True)

    event_date = Column(Date, nullable=False)
    effective_date = Column(Date, nullable=True)  
    from_value = Column(String(255), nullable=True)
    to_value = Column(String(255), nullable=True)

 
    from_department = Column(String(255), nullable=True)
    to_department = Column(String(255), nullable=True)
    from_designation = Column(String(255), nullable=True)
    to_designation = Column(String(255), nullable=True)
    from_grade = Column(String(100), nullable=True)
    to_grade = Column(String(100), nullable=True)
    from_location = Column(String(255), nullable=True)
    to_location = Column(String(255), nullable=True)
    from_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    to_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)

    # Salary revision fields
    from_salary = Column(String(50), nullable=True)   # stored as string to avoid decimal issues
    to_salary = Column(String(50), nullable=True)

    # Approval & audit
    initiated_by = Column(Integer, ForeignKey("employees.id"), nullable=True)  # HR user id
    approved_by = Column(Integer, ForeignKey("employees.id"), nullable=True)
    approval_status = Column(String(50), default="Approved")  # Pending / Approved / Rejected

    # Supporting info
    remarks = Column(Text, nullable=True)
    reference_document = Column(String(255), nullable=True)  # e.g. letter filename / URL

    is_active = Column(Boolean, default=True)  # soft-delete flag
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
