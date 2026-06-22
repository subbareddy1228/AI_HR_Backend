# model/HR_Operations/employee_confirmation.py
# Employee Confirmation — Tab 2 of Promotions & Career Progression
# Replaces the original stub

from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, Boolean
from core.database import Base
from datetime import datetime


class EmployeeConfirmation(Base):
    __tablename__ = "employee_confirmations"

    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Status: Pending Approval | Confirmed | Extended | Terminated
    status              = Column(String(50), nullable=False, default="Pending Approval")

    # 5-step workflow  (P → A → H → D → A in the UI)
    workflow_step       = Column(Integer, default=0)      # count of completed steps
    workflow_total      = Column(Integer, default=5)
    step_1_done         = Column(Boolean, default=False)  # P  - Profile review
    step_2_done         = Column(Boolean, default=False)  # A  - Attendance check
    step_3_done         = Column(Boolean, default=False)  # H  - HR interview
    step_4_done         = Column(Boolean, default=False)  # D  - Director approval
    step_5_done         = Column(Boolean, default=False)  # A  - Final approval

    # Due date & letter
    due_date            = Column(Date, nullable=True)
    confirmation_date   = Column(Date, nullable=True)

    # Performance: Exceeds Expectations | Meets Expectations | Needs Improvement | Unsatisfactory
    performance_rating  = Column(String(50), nullable=True)

    # Automation flags
    auto_triggered      = Column(Boolean, default=False)
    letter_sent         = Column(Boolean, default=False)

    reviewed_by         = Column(Integer, ForeignKey("employees.id"), nullable=True)
    remarks             = Column(Text, nullable=True)

    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
