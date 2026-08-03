from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, Boolean

from core.database import Base


class EmployeeBankDetail(Base):
    """One row per employee. Created/updated via the employee's own
    self-service profile-completion step (routers/Employee_Management/
    employee_self_service.py)."""

    __tablename__ = "employee_bank_details"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, unique=True, index=True)

    account_holder_name = Column(String(255), nullable=False)
    account_number = Column(String(50), nullable=False)
    ifsc_code = Column(String(20), nullable=False)
    bank_name = Column(String(255), nullable=False)
    branch_name = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class EmployeeEmergencyContact(Base):
    """One row per employee. Same self-service origin as bank details."""

    __tablename__ = "employee_emergency_contacts"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, unique=True, index=True)

    contact_name = Column(String(255), nullable=False)
    relationship = Column(String(100), nullable=False)
    phone_number = Column(String(20), nullable=False)
    alternate_phone_number = Column(String(20), nullable=True)
    address = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Announcement(Base):
    """Company-wide announcements. Created by HR-side roles, visible to
    every authenticated user in the same tenant (including 'employee')."""

    __tablename__ = "announcements"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, nullable=True, index=True)

    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    created_by_name = Column(String(255), nullable=True)
    is_active = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)