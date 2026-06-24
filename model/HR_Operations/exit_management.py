# model/HR_Operations/exit_management.py
# Exit Management & Clearance — replaces the original stub
#
# Tabs in frontend:
#   1. Exit Cases    — main exit record (clearance progress, pending items)
#   2. Alumni        — post-exit alumni network (rehire, boomerang, engagement)
#   3. Settlements   — final settlement amounts
#   4. Employee Exits — searchable exit history report
#   5. Trends        — exit trend analytics modal

from sqlalchemy import (
    Column, Integer, String, Date, Text,
    DateTime, ForeignKey, Numeric, Boolean,
)
from core.database import Base
from datetime import datetime


# ─────────────────────────────────────────────────────────────────────────────
#  Core exit record  (Tab 1 – Exit Cases)
# ─────────────────────────────────────────────────────────────────────────────
class ExitManagement(Base):
    __tablename__ = "exit_management"

    id                   = Column(Integer, primary_key=True, index=True)
    employee_id          = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Exit basics
    resignation_date     = Column(Date, nullable=False)
    last_working_date    = Column(Date, nullable=True)
    days_left            = Column(Integer, nullable=True)   # computed at query time

    # Exit type: Resignation | Termination | Retirement | Absconding | Better Opportunity
    exit_type            = Column(String(50), nullable=False)

    # Status: In Progress | Pending | Completed | Escalated | Cancelled
    status               = Column(String(30), nullable=False, default="In Progress")

    # Clearance progress 0-100 %
    clearance_progress   = Column(Integer, default=0)

    # Pending clearance items count (shown as badge in UI: 8+2, 1, etc.)
    pending_items        = Column(Integer, default=0)

    # Clearance checklist booleans
    it_clearance         = Column(Boolean, default=False)
    finance_clearance    = Column(Boolean, default=False)
    hr_clearance         = Column(Boolean, default=False)
    admin_clearance      = Column(Boolean, default=False)
    assets_returned      = Column(Boolean, default=False)
    exit_interview_done  = Column(Boolean, default=False)
    knowledge_transfer   = Column(Boolean, default=False)

    reason               = Column(Text, nullable=True)
    remarks              = Column(Text, nullable=True)

    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
#  Alumni  (Tab 2)
# ─────────────────────────────────────────────────────────────────────────────
class Alumni(Base):
    __tablename__ = "alumni"

    id              = Column(Integer, primary_key=True, index=True)
    exit_id         = Column(Integer, ForeignKey("exit_management.id"), nullable=False, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    # Auto-generated alumni code: ALM001, ALM002 …
    alumni_code     = Column(String(20), nullable=True, unique=True)

    exit_date       = Column(Date, nullable=True)

    # Rehire eligibility: Yes | No
    rehire_eligible = Column(Boolean, default=False)
    # Boomerang (returned to company): Yes | No
    boomerang       = Column(Boolean, default=False)
    # Engagement level: High | Medium | Low
    engagement      = Column(String(20), nullable=True, default="Medium")

    remarks         = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ─────────────────────────────────────────────────────────────────────────────
#  Settlement  (Tab 3)
# ─────────────────────────────────────────────────────────────────────────────
class Settlement(Base):
    __tablename__ = "settlements"

    id              = Column(Integer, primary_key=True, index=True)
    exit_id         = Column(Integer, ForeignKey("exit_management.id"), nullable=False, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=False, index=True)

    amount          = Column(Numeric(12, 2), nullable=False)
    settlement_date = Column(Date, nullable=True)

    # Status: Completed | In Progress | Pending
    status          = Column(String(30), nullable=False, default="Pending")

    remarks         = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
