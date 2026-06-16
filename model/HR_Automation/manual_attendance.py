"""
models/manual_attendance.py
SQLAlchemy ORM models for Manual Attendance module.

Manual Attendance = HR directly enters day-count values (P/A/H/W/CO/CL/LW)
per employee per month — NO time punches involved.

Two tables:
  ManualAttendanceRecord  — one row per employee per month
  ManualAttendanceImport  — audit log for CSV/Excel uploads
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date,
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


class ManualAttendanceRecord(Base):
    """
    One row per employee per month.
    Columns match exactly the 7 editable fields shown in the table:
      P  = Present days
      A  = Absent days
      H  = Holiday days
      W  = Week Off days
      CO = Comp Off days
      CL = Casual Leave days
      LW = Leave Without Pay days
    """
    __tablename__ = "manual_attendance_records"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(
        String(20),
        ForeignKey("employees.employee_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Period: stored as year + month (1-12), displayed as "SEP-2025"
    year        = Column(Integer, nullable=False)
    month       = Column(Integer, nullable=False)   # 1–12

    # Org filter fields (denormalized for fast filtering)
    business_unit = Column(String(100), default="")
    location      = Column(String(100), default="")
    cost_center   = Column(String(100), default="")
    department    = Column(String(100), default="")

    # ── 7 day-count columns (editable number inputs) ──
    present_days   = Column(Integer, default=0)   # P
    absent_days    = Column(Integer, default=0)   # A
    holiday_days   = Column(Integer, default=0)   # H
    week_off_days  = Column(Integer, default=0)   # W
    comp_off_days  = Column(Integer, default=0)   # CO
    casual_leave   = Column(Integer, default=0)   # CL
    leave_wo_pay   = Column(Integer, default=0)   # LW

    # Toggle in Action column (green toggle = saved/active)
    is_saved    = Column(Boolean, default=False)

    # Audit
    saved_by    = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at  = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(),
                         onupdate=func.now())

    employee    = relationship("Employee", back_populates="manual_attendance_records")

    __table_args__ = (
        UniqueConstraint("employee_id", "year", "month", name="uq_manual_attendance"),
        Index("ix_manual_att_period", "year", "month"),
        Index("ix_manual_att_dept",   "department"),
        Index("ix_manual_att_bu",     "business_unit"),
    )

    def __repr__(self):
        return (
            f"<ManualAttendanceRecord {self.employee_id} "
            f"{self.year}-{self.month:02d}>"
        )


class ManualAttendanceImport(Base):
    """
    Audit log for Options → Upload Attendance (CSV/Excel).
    Stores per-row errors so HR can review what failed.
    """
    __tablename__ = "manual_attendance_imports"

    id           = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename     = Column(String(255), nullable=False)
    period_year  = Column(Integer,  nullable=False)
    period_month = Column(Integer,  nullable=False)
    total_rows   = Column(Integer,  default=0)
    success_rows = Column(Integer,  default=0)
    failed_rows  = Column(Integer,  default=0)
    error_log    = Column(JSONB,    default=[])   # [{row, employee_id, error}]
    status       = Column(SAEnum(ImportStatusEnum), default=ImportStatusEnum.success)
    uploaded_by  = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at   = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        Index("ix_import_period", "period_year", "period_month"),
    )

    def __repr__(self):
        return (
            f"<ManualAttendanceImport {self.filename} "
            f"{self.period_year}-{self.period_month:02d} [{self.status}]>"
        )
