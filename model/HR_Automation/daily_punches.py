"""
models/daily_punches.py
SQLAlchemy ORM models for Daily Punches module.
Stack: FastAPI + PostgreSQL + SQLAlchemy
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date, Time,
    ForeignKey, Text, Numeric, Enum as SAEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from model.HR_Automation.attendance_capture import AttendanceStatusEnum
from model.HR_Automation.daily_attendance import PunchDirectionEnum
from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS — matched exactly to frontend Punch Legend
# ─────────────────────────────────────────────────────────

class PunchSourceEnum(str, enum.Enum):
    remote          = "remote"           # Remote punch
    selfie          = "selfie"           # Selfie / camera
    web_chat        = "web_chat"         # Web/Chat portal
    qr_scan         = "qr_scan"         # QR Scan
    biometric_fetch = "biometric_fetch"  # Biometric Fetch
    biometric_sync  = "biometric_sync"  # Biometric Sync
    manual          = "manual"           # Manual entry by HR
    excel_import    = "excel_import"     # Excel/CSV Import
    missed          = "missed"           # Missed punch (auto-flagged)
    time_relax      = "time_relax"       # Time Relax policy
    travel          = "travel"           # Travel punch
    api             = "api"              # API punch


# class PunchDirectionEnum(str, enum.Enum):
#     IN  = "IN"
#     OUT = "OUT"


class PunchStatusEnum(str, enum.Enum):
    processed = "processed"   # XX - Processed (green)
    pending   = "pending"     # XX - Pending   (red/orange)


# class AttendanceStatusEnum(str, enum.Enum):
#     P  = "P"   # Present
#     A  = "A"   # Absent
#     L  = "L"   # Late
#     HD = "HD"  # Half Day
#     WO = "WO"  # Week Off
#     H  = "H"   # Holiday
#     OD = "OD"  # On Duty


# ─────────────────────────────────────────────────────────
# EMPLOYEE PUNCH  (one row per punch event)
# ─────────────────────────────────────────────────────────

class EmployeePunch(Base):
    __tablename__ = "employee_punches"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    employee_id     = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)

    # Date & time
    punch_date      = Column(Date, nullable=False, index=True)
    punch_time      = Column(DateTime(timezone=True), nullable=False)

    # Direction & source
    direction       = Column(SAEnum(PunchDirectionEnum), nullable=False)  # IN / OUT
    source          = Column(SAEnum(PunchSourceEnum), nullable=False, default=PunchSourceEnum.manual)

    # Processing status (Processed / Pending legend)
    status          = Column(SAEnum(PunchStatusEnum), default=PunchStatusEnum.pending, nullable=False)

    # Location data (GPS pin icon on row)
    latitude        = Column(Numeric(10, 7), nullable=True)
    longitude       = Column(Numeric(10, 7), nullable=True)
    location_url    = Column(Text, default="")         # Google Maps embed URL
    location_name   = Column(String(200), default="")  # Resolved location string

    # Selfie / face image (camera icon on row)
    selfie_path         = Column(String(500), nullable=True)   # S3 key or local path
    registered_face_path= Column(String(500), nullable=True)   # Reference face for comparison

    # HR override fields (Add Punch modal)
    remarks         = Column(Text, default="")
    is_manual       = Column(Boolean, default=False)           # Added manually by HR
    added_by        = Column(Integer, nullable=True)

    # Excel import reference
    import_batch_id = Column(UUID(as_uuid=True), nullable=True, index=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    employee        = relationship("Employee", back_populates="employee_punches")

    __table_args__ = (
        Index("ix_emp_punch_date",    "employee_id", "punch_date"),
        Index("ix_emp_punch_source",  "source"),
        Index("ix_emp_punch_status",  "status"),
        Index("ix_emp_punch_batch",   "import_batch_id"),
    )

    def __repr__(self):
        return f"<EmployeePunch {self.employee_id} {self.direction} @ {self.punch_time}>"


# ─────────────────────────────────────────────────────────
# DAILY PUNCH SUMMARY  (aggregated per employee per date)
# One row = one employee's full day view shown in the table
# ─────────────────────────────────────────────────────────

class DailyPunchSummary(Base):
    __tablename__ = "daily_punch_summaries"

    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"), nullable=False)
    punch_date          = Column(Date, nullable=False, index=True)

    # Computed from raw punches
    first_in_time       = Column(DateTime(timezone=True), nullable=True)   # Start column
    last_out_time       = Column(DateTime(timezone=True), nullable=True)   # End column
    duration_minutes    = Column(Integer, default=0)                        # Duration column

    # Attendance badge (P / A / L / HD / WO / H / OD)
    attendance_status   = Column(SAEnum(AttendanceStatusEnum), default=AttendanceStatusEnum.absent)

    # Org filters (for the 4 dropdown filters)
    business_unit       = Column(String(100), default="Default Business Units")
    location            = Column(String(100), default="")
    cost_center         = Column(String(100), default="")
    department          = Column(String(100), default="")

    # Start / End GPS presence flags
    has_start_selfie    = Column(Boolean, default=False)
    has_start_location  = Column(Boolean, default=False)
    has_end_selfie      = Column(Boolean, default=False)
    has_end_location    = Column(Boolean, default=False)

    punch_count         = Column(Integer, default=0)
    is_late             = Column(Boolean, default=False)
    late_minutes        = Column(Integer, default=0)

    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    updated_at          = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee            = relationship("Employee", back_populates="daily_punch_summaries")

    __table_args__ = (
        UniqueConstraint("employee_id", "punch_date", name="uq_daily_punch_summary"),
        Index("ix_daily_summary_attendance", "attendance_status"),
        Index("ix_daily_summary_location",   "location"),
        Index("ix_daily_summary_dept",       "department"),
        Index("ix_daily_summary_bu",         "business_unit"),
    )

    def __repr__(self):
        return f"<DailyPunchSummary {self.employee_id} {self.punch_date} {self.attendance_status}>"


# ─────────────────────────────────────────────────────────
# PUNCH IMPORT BATCH  (Excel / CSV imports)
# ─────────────────────────────────────────────────────────

class PunchImportBatch(Base):
    __tablename__ = "punch_import_batches"

    id              = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    filename        = Column(String(255), nullable=False)
    uploaded_by     = Column(Integer, nullable=True)
    total_rows      = Column(Integer, default=0)
    success_rows    = Column(Integer, default=0)
    failed_rows     = Column(Integer, default=0)
    error_log       = Column(JSONB, default=[])   # list of {row, error}
    created_at      = Column(DateTime(timezone=True), server_default=func.now())

    def __repr__(self):
        return f"<PunchImportBatch {self.filename} {self.created_at}>"
