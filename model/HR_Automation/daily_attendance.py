"""
models/daily_attendance.py
SQLAlchemy ORM models for Daily Attendance module.
Stack: FastAPI + PostgreSQL + SQLAlchemy

Key differences from Daily Punches:
- Daily Punches  → raw punch-by-punch log table (what time each punch happened)
- Daily Attendance → card-view with shift timeline, status label, in-time duration,
                     add-punch modal, all-punches modal (per employee per day)
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Time,
    ForeignKey, Text, Numeric, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────

class AttendanceStatusEnum(str, enum.Enum):
    Present  = "Present"
    Absent   = "Absent"
    Late     = "Late"
    Half_Day = "Half Day"
    Week_Off = "Week Off"
    Holiday  = "Holiday"
    On_Duty  = "On Duty"


class PunchTypeEnum(str, enum.Enum):
    selfie  = "selfie"
    remote  = "remote"
    manual  = "manual"
    qr_scan = "qr_scan"
    api     = "api"
    biometric = "biometric"


class PunchDirectionEnum(str, enum.Enum):
    IN  = "IN"
    OUT = "OUT"


class ShiftTypeEnum(str, enum.Enum):
    general  = "General"
    morning  = "Morning"
    evening  = "Evening"
    night    = "Night"
    flexible = "Flexible"


# ─────────────────────────────────────────────────────────
# DAILY ATTENDANCE RECORD
# One row per employee per date — the card shown in the UI
# ─────────────────────────────────────────────────────────

class DailyAttendanceRecord(Base):
    __tablename__ = "daily_attendance_records"

    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(
        String(20),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
    )
    attendance_date     = Column(Date, nullable=False, index=True)

    # ── Status & note (left panel of the card) ──
    status              = Column(SAEnum(AttendanceStatusEnum), nullable=False,
                                 default=AttendanceStatusEnum.Absent)
    note                = Column(Text, default="")   # e.g. "Present marked as at least one time-punch was found"

    # ── Org metadata (shown in card header: location / designation / dept) ──
    location            = Column(String(100), default="")
    business_unit       = Column(String(100), default="")
    cost_center         = Column(String(100), default="")
    department          = Column(String(100), default="")

    # ── Shift info (shown as "General" label above timeline) ──
    shift_type          = Column(SAEnum(ShiftTypeEnum), default=ShiftTypeEnum.general)
    shift_start         = Column(Time, nullable=True)   # e.g. 09:00
    shift_end           = Column(Time, nullable=True)   # e.g. 18:00

    # ── Timeline display values (green / blue / yellow bars) ──
    timeline_start      = Column(String(10), default="03:00A")  # leftmost green bar start
    timeline_end        = Column(String(10), default="12:00A")  # rightmost yellow bar end

    # ── Punch In / Punch Out (shown below the timeline bars) ──
    punch_in_time       = Column(DateTime(timezone=True), nullable=True)  # e.g. 09:17A
    punch_out_time      = Column(DateTime(timezone=True), nullable=True)  # e.g. 06:05P
    punch_type          = Column(SAEnum(PunchTypeEnum), nullable=True)    # Selfie / Manual / …

    # ── In-Time (right panel: "8 h 35 m") ──
    in_time_minutes     = Column(Integer, default=0)   # total worked minutes; display as H h MM m

    # ── Late info ──
    is_late             = Column(Boolean, default=False)
    late_minutes        = Column(Integer, default=0)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(),
                                 onupdate=func.now())

    # relationships
    employee            = relationship("Employee", back_populates="daily_attendance_records")
    punches             = relationship(
        "AttendancePunchEntry",
        back_populates="daily_record",
        cascade="all, delete-orphan",
        order_by="AttendancePunchEntry.punch_time",
    )

    __table_args__ = (
        UniqueConstraint("employee_id", "attendance_date", name="uq_daily_attendance"),
        Index("ix_da_status",   "status"),
        Index("ix_da_location", "location"),
        Index("ix_da_dept",     "department"),
        Index("ix_da_bu",       "business_unit"),
    )

    def __repr__(self):
        return f"<DailyAttendanceRecord {self.employee_id} {self.attendance_date} {self.status}>"


# ─────────────────────────────────────────────────────────
# ATTENDANCE PUNCH ENTRY
# Individual punch events shown in the "All Punches" (…) modal
# ─────────────────────────────────────────────────────────

class AttendancePunchEntry(Base):
    __tablename__ = "attendance_punch_entries"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    daily_record_id = Column(
        Integer,
        ForeignKey("daily_attendance_records.id", ondelete="CASCADE"),
        nullable=False,
    )
    employee_id     = Column(String(20), nullable=False, index=True)
    punch_time      = Column(DateTime(timezone=True), nullable=False)
    direction       = Column(SAEnum(PunchDirectionEnum), nullable=False)
    punch_type      = Column(SAEnum(PunchTypeEnum), default=PunchTypeEnum.manual)
    remarks         = Column(Text, default="")
    is_manual       = Column(Boolean, default=False)   # added via modal
    added_by        = Column(Integer, ForeignKey("user.id", ondelete="SET NULL"), nullable=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    daily_record    = relationship("DailyAttendanceRecord", back_populates="punches")

    __table_args__ = (
        Index("ix_punch_entry_record",   "daily_record_id"),
        Index("ix_punch_entry_emp_time", "employee_id", "punch_time"),
    )

    def __repr__(self):
        return f"<AttendancePunchEntry {self.employee_id} {self.direction} @ {self.punch_time}>"
