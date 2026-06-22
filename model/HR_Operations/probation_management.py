# model/HR_Operations/probation_management.py
# Probation Management — Tab 1 of Promotions & Career Progression

from sqlalchemy import Column, Integer, String, Date, Text, DateTime, ForeignKey, Boolean
from core.database import Base
from datetime import datetime


class ProbationManagement(Base):
    __tablename__ = "probation_management"

    id                   = Column(Integer, primary_key=True, index=True)
    employee_id          = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Probation window
    probation_start_date = Column(Date, nullable=False)
    probation_end_date   = Column(Date, nullable=False)
    extended_end_date    = Column(Date, nullable=True)   # filled when status = Extended

    # Review milestones  (Exceeds | Meets | Needs | N/A)
    milestone_30_status  = Column(String(30), nullable=True)
    milestone_60_status  = Column(String(30), nullable=True)
    milestone_90_status  = Column(String(30), nullable=True)
    milestone_30_date    = Column(Date, nullable=True)
    milestone_60_date    = Column(Date, nullable=True)
    milestone_90_date    = Column(Date, nullable=True)

    # Progress & risk
    progress_percentage  = Column(Integer, default=0)          # 0-100
    risk_level           = Column(String(20), nullable=False, default="Low")  # Low | Medium | High
    # In Progress | At Risk | Ending Soon | Extended | Completed | Terminated
    status               = Column(String(30), nullable=False, default="In Progress")

    # Supporting roles
    buddy_id             = Column(Integer, ForeignKey("employees.id"), nullable=True)
    reviewed_by          = Column(Integer, ForeignKey("employees.id"), nullable=True)
    review_date          = Column(Date, nullable=True)
    remarks              = Column(Text, nullable=True)
    auto_scheduled       = Column(Boolean, default=False)

    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
