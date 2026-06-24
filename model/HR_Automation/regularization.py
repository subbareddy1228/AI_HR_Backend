"""
models/regularization.py
SQLAlchemy ORM models for Regularization Workflow module.

Covers all 4 tabs:
  Tab 1 — Requests       : RegularizationRequest, ApprovalWorkflowStep
  Tab 2 — Settings       : AutoRejectRule
  Tab 3 — Bulk Processing: BulkRegularizationProcess
  Tab 4 — Reports        : RegularizationReport
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Time,
    ForeignKey, Text, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from model.HR_Automation.attendance_capture import PunchTypeEnum
from core.database import Base
from model.HR_Automation.attendance_reports import ReportFormatEnum

# ─────────────────────────────────────────────────────────
# ENUMS — from component's requestType options + status values
# ─────────────────────────────────────────────────────────

class RequestTypeEnum(str, enum.Enum):
    missing   = "missing"     # Missing Punch
    incorrect = "incorrect"   # Incorrect Time
    forgot    = "forgot"      # Forgot Punch
    wfh       = "wfh"         # WFH Regularization
    on_duty   = "on_duty"     # On-Duty


class RequestStatusEnum(str, enum.Enum):
    pending       = "pending"
    approved      = "approved"
    rejected      = "rejected"
    auto_rejected = "auto-rejected"


# class PunchTypeEnum(str, enum.Enum):
#     IN  = "IN"
#     OUT = "OUT"


class DutyTypeEnum(str, enum.Enum):
    client_visit    = "client_visit"
    training        = "training"
    business_travel = "business_travel"
    other           = "other"


class IssueTypeEnum(str, enum.Enum):
    system  = "system"
    device  = "device"
    sync    = "sync"
    network = "network"
    other   = "other"


# class ReportFormatEnum(str, enum.Enum):
#     pdf   = "pdf"
#     excel = "excel"
#     csv   = "csv"


# ─────────────────────────────────────────────────────────
# TAB 1 — REGULARIZATION REQUEST
# ─────────────────────────────────────────────────────────

class RegularizationRequest(Base):
    __tablename__ = "regularization_requests"

    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(
        Integer, ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Type + status
    request_type     = Column(SAEnum(RequestTypeEnum), nullable=False, index=True)
    status           = Column(SAEnum(RequestStatusEnum),
                               default=RequestStatusEnum.pending, index=True)

    # ── Type-specific fields (all nullable; used based on request_type) ──

    # missing punch
    date_time        = Column(DateTime(timezone=True), nullable=True)

    # incorrect time
    original_time    = Column(DateTime(timezone=True), nullable=True)
    corrected_time   = Column(DateTime(timezone=True), nullable=True)

    # forgot punch
    punch_date       = Column(Date, nullable=True)
    punch_type       = Column(SAEnum(PunchTypeEnum), nullable=True)
    approx_time      = Column(String(10), nullable=True)   # "HH:MM"

    # wfh regularization
    wfh_date         = Column(Date, nullable=True)
    location         = Column(String(200), nullable=True)
    work_summary     = Column(Text, nullable=True)

    # on-duty
    od_date          = Column(Date, nullable=True)
    from_time        = Column(String(10), nullable=True)   # "HH:MM"
    to_time          = Column(String(10), nullable=True)
    duty_type        = Column(SAEnum(DutyTypeEnum), nullable=True)
    purpose          = Column(String(500), nullable=True)

    # Common fields
    reason           = Column(Text, nullable=False)
    remarks          = Column(Text, nullable=False)
    attachment_path  = Column(String(500), nullable=True)
    attachments      = Column(JSONB, default=[])

    # Approval workflow snapshot (list of levels)
    approval_workflow = Column(JSONB, default=[
        {"level": 1, "approver": "Manager", "status": "pending", "required": True},
        {"level": 2, "approver": "HR",      "status": "pending", "required": True},
    ])

    # Decision
    approved_at      = Column(DateTime(timezone=True), nullable=True)
    approved_by      = Column(Integer, nullable=True)
    rejected_at      = Column(DateTime(timezone=True), nullable=True)
    rejected_by      = Column(Integer, nullable=True)
    rejection_reason = Column(Text, nullable=True)
    is_auto_rejected = Column(Boolean, default=False)

    # Audit
    submitted_at     = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    submitted_by     = Column(String(100), default="")
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                               onupdate=func.now())
    created_by       = Column(Integer, nullable=True)

    employee         = relationship("Employee", back_populates="regularization_requests")

    __table_args__ = (
        Index("ix_reg_req_type_status", "request_type", "status"),
        Index("ix_reg_req_submitted",   "submitted_at"),
    )

    def __repr__(self):
        return (
            f"<RegularizationRequest {self.employee_id} "
            f"{self.request_type} [{self.status}]>"
        )


# ─────────────────────────────────────────────────────────
# TAB 2 — AUTO-REJECT RULES
# ─────────────────────────────────────────────────────────

class AutoRejectRule(Base):
    """
    Settings tab — Auto-Reject Rules table.
    Columns: Request Type | Days | Status (Enabled/Disabled) | Actions (Enable/Disable)
    Seeded with 2 default rules matching the component's initialState.
    """
    __tablename__ = "auto_reject_rules"

    id           = Column(Integer, primary_key=True, index=True)
    request_type = Column(SAEnum(RequestTypeEnum), nullable=False, unique=True)
    days         = Column(Integer, nullable=False, default=7)
    enabled      = Column(Boolean, default=True)
    updated_at   = Column(DateTime(timezone=True), server_default=func.now(),
                           onupdate=func.now())
    updated_by   = Column(Integer, nullable=True)

    def __repr__(self):
        return f"<AutoRejectRule {self.request_type} {self.days}d [{self.enabled}]>"


# ─────────────────────────────────────────────────────────
# TAB 3 — BULK REGULARIZATION PROCESS
# ─────────────────────────────────────────────────────────

class BulkRegularizationProcess(Base):
    """
    Bulk Processing tab — history table.
    Columns: Date Range | Issue Type | Processed | Status | Processed By
    """
    __tablename__ = "bulk_regularization_processes"

    id              = Column(Integer, primary_key=True, index=True)
    from_date       = Column(Date, nullable=False)
    to_date         = Column(Date, nullable=False)
    issue_type      = Column(SAEnum(IssueTypeEnum), nullable=False)
    employee_ids    = Column(JSONB, default=[])   # empty = all employees
    file_path       = Column(String(500), nullable=True)
    processed_count = Column(Integer, default=0)
    status          = Column(String(20), default="completed")
    processed_at    = Column(DateTime(timezone=True), server_default=func.now())
    processed_by    = Column(Integer, nullable=True)
    processed_by_name= Column(String(100), default="HR Admin")

    __table_args__ = (
        Index("ix_bulk_dates", "from_date", "to_date"),
    )

    def __repr__(self):
        return (
            f"<BulkRegularizationProcess {self.from_date}→{self.to_date} "
            f"{self.issue_type} [{self.processed_count} emp]>"
        )


# ─────────────────────────────────────────────────────────
# TAB 4 — REGULARIZATION REPORT
# ─────────────────────────────────────────────────────────

class RegularizationReport(Base):
    """
    Reports tab — Generated Reports history table.
    Columns: Date Range | Type | Format | Generated At | File Name | Total Records
    """
    __tablename__ = "regularization_reports"

    id            = Column(Integer, primary_key=True, index=True)
    from_date     = Column(Date, nullable=False)
    to_date       = Column(Date, nullable=False)
    request_type  = Column(SAEnum(RequestTypeEnum), nullable=True)   # None = All Types
    format        = Column(SAEnum(ReportFormatEnum), default=ReportFormatEnum.pdf)
    file_name     = Column(String(255), nullable=False)
    file_path     = Column(String(500), nullable=True)
    total_records = Column(Integer, default=0)
    summary       = Column(JSONB, default={})
    generated_at  = Column(DateTime(timezone=True), server_default=func.now())
    generated_by  = Column(Integer, nullable=True)
    generated_by_name = Column(String(100), default="HR Admin")

    __table_args__ = (
        Index("ix_report_dates", "from_date", "to_date"),
    )
