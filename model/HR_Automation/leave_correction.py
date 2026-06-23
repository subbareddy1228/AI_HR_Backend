"""
models/leave_correction.py
SQLAlchemy ORM models for Leave Correction module.

The UI shows a ledger table per employee per leave-type per month:
  OPENING | ACTIVITY | CORRECTION (editable) | CLOSING

Tables:
  LeaveCorrectionRecord  — one row per employee + leave_type + period
  LeaveCorrectionImport  — audit log for XLSX/CSV uploads
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date,
    ForeignKey, Text, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


class ImportStatusEnum(str, enum.Enum):
    success = "success"
    partial = "partial"
    failed  = "failed"


class LeaveCorrectionRecord(Base):
    """
    One row in the Leave Correction ledger.
    Unique per: employee_id + leave_type_code + year + month

    Columns visible in the UI:
      OPENING    — balance at start of period (read-only)
      ACTIVITY   — approved leaves taken this period (read-only, with ℹ icon)
      CORRECTION — HR-editable adjustment (+/- days)
      CLOSING    — computed: opening + activity + correction  (read-only)
    """
    __tablename__ = "leave_correction_records"

    id               = Column(Integer, primary_key=True, index=True)
    employee_id      = Column(
        String(20),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )

    # Leave type (matches the dropdown: "LV458 - Comp Off", "LV454 - Present", …)
    leave_type_code  = Column(String(20),  nullable=False)   # e.g. "LV458"
    leave_type_label = Column(String(100), nullable=False)   # e.g. "LV458 - Comp Off"

    # Period
    year             = Column(Integer, nullable=False)
    month            = Column(Integer, nullable=False)        # 1–12

    # Org filters (denormalized from Employee for fast filtering)
    business_unit    = Column(String(100), default="")
    location         = Column(String(100), default="")
    cost_center      = Column(String(100), default="")
    department       = Column(String(100), default="")

    # Ledger columns
    opening          = Column(Float, default=0.0)    # balance at period start
    activity         = Column(Float, default=0.0)    # approved leaves used
    correction       = Column(Float, default=0.0)    # HR adjustment (can be negative)
    closing          = Column(Float, default=0.0)    # opening + activity + correction

    # Save state (green circle button)
    is_saved         = Column(Boolean, default=False)
    saved_by         = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    saved_at         = Column(DateTime(timezone=True), nullable=True)

    # Audit
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    updated_at       = Column(DateTime(timezone=True), server_default=func.now(),
                               onupdate=func.now())

    employee         = relationship("Employee", back_populates="leave_correction_records")

    __table_args__ = (
        UniqueConstraint(
            "employee_id", "leave_type_code", "year", "month",
            name="uq_leave_correction",
        ),
        Index("ix_lc_period",        "year", "month"),
        Index("ix_lc_leave_type",    "leave_type_code"),
        Index("ix_lc_dept",          "department"),
        Index("ix_lc_bu",            "business_unit"),
    )

    def __repr__(self):
        return (
            f"<LeaveCorrectionRecord {self.employee_id} "
            f"{self.leave_type_code} "
            f"{self.year}-{self.month:02d} corr={self.correction}>"
        )


class LeaveCorrectionImport(Base):
    """
    Audit log for Options → Upload (XLSX/XLS/CSV).
    Per-row errors let HR identify which rows failed.
    """
    __tablename__ = "leave_correction_imports"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename        = Column(String(255), nullable=False)
    period_year     = Column(Integer, nullable=False)
    period_month    = Column(Integer, nullable=False)
    leave_type_code = Column(String(20), nullable=True)
    total_rows      = Column(Integer, default=0)
    success_rows    = Column(Integer, default=0)
    failed_rows     = Column(Integer, default=0)
    error_log       = Column(JSONB, default=[])     # [{row, employee_id, error}]
    status          = Column(SAEnum(ImportStatusEnum), default=ImportStatusEnum.success)
    uploaded_by     = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_lc_import_period", "period_year", "period_month"),
    )
