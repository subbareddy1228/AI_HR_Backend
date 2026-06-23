"""
models/monthly_attendance.py
SQLAlchemy ORM models for Monthly Attendance module.
Stack: FastAPI + PostgreSQL + SQLAlchemy

Two tables:
  MonthlyAttendanceCell  — one row per employee per calendar day
                           (the coloured cell in the calendar grid)
  MonthlyAttendanceSummary — one row per employee per month
                             (aggregated counts for export)
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date,
    ForeignKey, Text, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS — all legend codes visible in the UI
# ─────────────────────────────────────────────────────────

class DayStatusEnum(str, enum.Enum):
    P  = "P"   # LV454 - Present          → teal   #d1f5ee
    A  = "A"   # LV455 - Absent           → red    #fcdada
    H  = "H"   # LV456 - Holiday          → green  #d4edda
    W  = "W"   # LV457 - Week Off         → grey   #e0e0e0
    CO = "CO"  # LV458 - Comp Off         → yellow
    CL = "CL"  # LV459 - Casual Leave     → blue
    LW = "LW"  # LV1055 - Leave w/o Pay   → secondary
    SL = "SL"  # LV2638 - Sick Leave      → info
    HD = "HD"  # LV2640 - Half Day        → warning
    L  = "L"   # Late (not in legend but used in daily modules)


# ─────────────────────────────────────────────────────────
# MONTHLY ATTENDANCE CELL
# One row per employee per calendar day — drives the calendar grid
# ─────────────────────────────────────────────────────────

class MonthlyAttendanceCell(Base):
    __tablename__ = "monthly_attendance_cells"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(
        String(20),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    cell_date       = Column(Date, nullable=False, index=True)  # actual date of the day

    # Status shown inside the cell (P / A / H / W / CO / CL / LW / SL / HD)
    status          = Column(SAEnum(DayStatusEnum), nullable=False, default=DayStatusEnum.A)

    # Clock icon shown at top-right corner of cell when True
    has_punch       = Column(Boolean, default=False)

    # Optional: store the leave code reference for coloured display
    leave_code      = Column(String(10), nullable=True)   # e.g. "LV454"
    leave_label     = Column(String(50), nullable=True)   # e.g. "Present"

    # Working minutes for this day (used by Recalculate)
    worked_minutes  = Column(Integer, default=0)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now())

    employee        = relationship("Employee", back_populates="monthly_cells")

    __table_args__ = (
        UniqueConstraint("employee_id", "cell_date", name="uq_monthly_cell"),
        Index("ix_cell_status",      "status"),
        Index("ix_cell_emp_date",    "employee_id", "cell_date"),
    )

    def __repr__(self):
        return f"<MonthlyAttendanceCell {self.employee_id} {self.cell_date} {self.status}>"


# ─────────────────────────────────────────────────────────
# MONTHLY ATTENDANCE SUMMARY
# Aggregated counts per employee per month — used for export & stats
# ─────────────────────────────────────────────────────────

class MonthlyAttendanceSummary(Base):
    __tablename__ = "monthly_attendance_summaries"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(
        String(20),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    year            = Column(Integer, nullable=False)
    month           = Column(Integer, nullable=False)   # 1–12

    # Day counts (one column per legend code)
    present_days    = Column(Integer, default=0)
    absent_days     = Column(Integer, default=0)
    holiday_days    = Column(Integer, default=0)
    week_off_days   = Column(Integer, default=0)
    comp_off_days   = Column(Integer, default=0)
    casual_leave    = Column(Integer, default=0)
    leave_wo_pay    = Column(Integer, default=0)
    sick_leave      = Column(Integer, default=0)
    half_days       = Column(Integer, default=0)
    late_days       = Column(Integer, default=0)

    total_worked_minutes = Column(Integer, default=0)

    recalculated_at = Column(DateTime(timezone=True), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                             onupdate=func.now())

    employee        = relationship("Employee", back_populates="monthly_summaries")

    __table_args__ = (
        UniqueConstraint("employee_id", "year", "month", name="uq_monthly_summary"),
        Index("ix_summary_year_month", "year", "month"),
    )

    def __repr__(self):
        return f"<MonthlyAttendanceSummary {self.employee_id} {self.year}-{self.month:02d}>"
