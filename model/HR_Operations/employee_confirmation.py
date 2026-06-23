"""
model/HR_Operations/employee_confirmation.py

Employee Confirmation Management
---------------------------------
Two tables:

1. EmployeeConfirmation        -> one row per probation/confirmation case
2. ConfirmationApprovalStage   -> the 4-stage approval chain per case
                                   (Manager -> HR -> Dept Head -> Authority),
                                   stored as separate rows so the number of
                                   stages and their order stay flexible.
"""

from sqlalchemy import (
    Column,
    Integer,
    String,
    Date,
    Text,
    DateTime,
    ForeignKey,
)
from core.database import Base
from datetime import datetime


# ======================================================
# 1. EMPLOYEE CONFIRMATION (core record)
# ======================================================
class EmployeeConfirmation(Base):
    __tablename__ = "employee_confirmations"

    id = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    probation_start_date = Column(Date, nullable=False)
    probation_end_date = Column(Date, nullable=False)     # = due date shown in "Time Status"
    confirmation_date = Column(Date, nullable=True)

    performance_rating = Column(String(20), nullable=True)   # EXCELLENT | GOOD | SATISFACTORY | POOR

    # PENDING_REVIEW | UNDER_REVIEW | PENDING_APPROVAL | CONFIRMED | EXTENDED | OVERDUE | IN_PROGRESS | TERMINATED
    status = Column(String(50), nullable=False, server_default="PENDING_REVIEW")

    # ELIGIBLE | CONDITIONAL | NOT_ELIGIBLE -> auto-computed, see service layer
    eligibility = Column(String(20), nullable=False, server_default="ELIGIBLE")

    extension_count = Column(Integer, nullable=False, server_default="0")   # powers "Extended 1x"
    extended_till = Column(Date, nullable=True)

    # manager's recommendation shown under the approval workflow row
    # RECOMMENDED | CONDITIONAL | NOT_RECOMMENDED | PENDING
    manager_recommendation = Column(String(20), nullable=False, server_default="PENDING")

    reporting_manager_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    reviewed_by = Column(Integer, ForeignKey("employees.id"), nullable=True)

    last_reminder_sent_at = Column(DateTime, nullable=True)

    remarks = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ======================================================
# 2. CONFIRMATION APPROVAL STAGE  (Manager -> HR -> Dept Head -> Authority)
# ======================================================
class ConfirmationApprovalStage(Base):
    __tablename__ = "confirmation_approval_stages"

    id = Column(Integer, primary_key=True, index=True)
    confirmation_id = Column(
        Integer, ForeignKey("employee_confirmations.id"), nullable=False, index=True
    )

    stage_name = Column(String(50), nullable=False)   # MANAGER | HR | DEPT_HEAD | AUTHORITY
    stage_order = Column(Integer, nullable=False)      # 1, 2, 3, 4 -> display order

    # PENDING | APPROVED | REJECTED
    status = Column(String(20), nullable=False, server_default="PENDING")

    approver_id = Column(Integer, ForeignKey("employees.id"), nullable=True)
    acted_at = Column(DateTime, nullable=True)
    remarks = Column(Text, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)