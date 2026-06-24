"""
models/holiday_calendar.py
SQLAlchemy ORM models for Holiday Calendar module.

Covers all 5 tabs visible in screenshots:
  Tab 1 — Holiday Master        : Holiday
  Tab 2 — Optional Applications : OptionalHolidayApplication
  Tab 3 — Calendars             : HolidayCalendar
  Tab 4 — Holiday Swap          : HolidaySwapRequest
  Tab 5 — Carry Forward         : HolidayCarryForward
"""

from sqlalchemy import (
    Column, String, Integer, Boolean, DateTime, Date,
    ForeignKey, Text, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from model.HR_Automation.shift_management import SwapStatusEnum
from model.HR_Automation.leave_management import ApplicationStatusEnum
from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS — exact values from component
# ─────────────────────────────────────────────────────────

class HolidayTypeEnum(str, enum.Enum):
    gazetted   = "gazetted"
    restricted = "restricted"
    festival   = "festival"


class CategoryEnum(str, enum.Enum):
    public_holiday     = "Public Holiday"
    national_holiday   = "National Holiday"
    festival           = "Festival"
    state_holiday      = "State Holiday"
    regional_holiday   = "Regional Holiday"
    local_holiday      = "Local Holiday"
    company_holiday    = "Company Holiday"
    restricted_holiday = "Restricted Holiday"


# class ApplicationStatusEnum(str, enum.Enum):
#     Pending  = "Pending"
#     Approved = "Approved"
#     Rejected = "Rejected"


# class SwapStatusEnum(str, enum.Enum):
#     pending  = "pending"
#     approved = "approved"
#     rejected = "rejected"


class CarryForwardStatusEnum(str, enum.Enum):
    processed = "processed"
    pending   = "pending"


# ─────────────────────────────────────────────────────────
# TAB 1 — HOLIDAY MASTER
# ─────────────────────────────────────────────────────────

class Holiday(Base):
    __tablename__ = "holidays"

    id                    = Column(Integer, primary_key=True, index=True)
    name                  = Column(String(200), nullable=False)
    date                  = Column(Date, nullable=False, index=True)
    location              = Column(String(100), default="All")   # "India" | "Bangalore" | "All"
    category              = Column(String(100), nullable=False)
    holiday_type          = Column(SAEnum(HolidayTypeEnum),
                                   default=HolidayTypeEnum.gazetted)
    optional              = Column(Boolean, default=False)

    # Optional-specific fields
    advance_booking_days  = Column(Integer, default=0)
    allow_carry_forward   = Column(Boolean, default=False)
    carry_forward_limit   = Column(Integer, default=0)

    # Scope
    applicable_calendars  = Column(JSONB, default=["all"])
    applicable_groups     = Column(JSONB, default=["all"])

    # Audit
    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    created_by            = Column(Integer, nullable=True)
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(),
                                   onupdate=func.now())

    __table_args__ = (
        Index("ix_holiday_date",     "date"),
        Index("ix_holiday_category", "category"),
        Index("ix_holiday_optional", "optional"),
    )

    def __repr__(self):
        return f"<Holiday {self.name} {self.date} [{self.holiday_type}]>"


# ─────────────────────────────────────────────────────────
# TAB 2 — OPTIONAL APPLICATIONS
# ─────────────────────────────────────────────────────────

class OptionalHolidayApplication(Base):
    __tablename__ = "optional_holiday_applications"

    id              = Column(Integer, primary_key=True, index=True)
    holiday_id      = Column(Integer, ForeignKey("holidays.id", ondelete="CASCADE"),
                              nullable=False)
    employee_id     = Column(Integer,
                              ForeignKey("employees.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    employee_name   = Column(String(100), default="")   # denormalized for display

    # Table columns: HOLIDAY · DATE · APPLIED ON · STATUS · REASON
    holiday_name    = Column(String(200), default="")   # denormalized
    holiday_date    = Column(Date, nullable=False)
    applied_date    = Column(Date, nullable=False)
    reason          = Column(Text, default="")
    status          = Column(SAEnum(ApplicationStatusEnum),
                              default=ApplicationStatusEnum.pending, index=True)

    # Approval workflow
    approval_required   = Column(Boolean, default=True)
    approval_workflow   = Column(JSONB, default=[
        {"level": 1, "approver": "Manager", "status": "pending", "required": True},
        {"level": 2, "approver": "HR",      "status": "pending", "required": True},
    ])

    # Decision
    approved_at     = Column(DateTime(timezone=True), nullable=True)
    approved_by     = Column(String(100), nullable=True)
    rejected_at     = Column(DateTime(timezone=True), nullable=True)
    rejected_by     = Column(String(100), nullable=True)

    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now())

    holiday         = relationship("Holiday")
    employee        = relationship("Employee", back_populates="optional_holiday_applications")

    __table_args__ = (
        Index("ix_opt_app_status", "status"),
        Index("ix_opt_app_employee","employee_id"),
    )

    def __repr__(self):
        return (
            f"<OptionalHolidayApplication emp={self.employee_id} "
            f"{self.holiday_name} [{self.status}]>"
        )


# ─────────────────────────────────────────────────────────
# TAB 3 — HOLIDAY CALENDARS
# ─────────────────────────────────────────────────────────

class HolidayCalendar(Base):
    __tablename__ = "holiday_calendars"

    id              = Column(Integer, primary_key=True, index=True)
    name            = Column(String(200), nullable=False)
    location        = Column(String(100), default="All")
    employee_groups = Column(JSONB, default=["all"])
    is_default      = Column(Boolean, default=False, index=True)
    is_active       = Column(Boolean, default=True)
    created_at      = Column(DateTime(timezone=True), server_default=func.now())
    created_by      = Column(Integer, nullable=True)
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now())

    def __repr__(self):
        return f"<HolidayCalendar {self.name} [{self.location}]>"


# ─────────────────────────────────────────────────────────
# TAB 4 — HOLIDAY SWAP
# ─────────────────────────────────────────────────────────

class HolidaySwapRequest(Base):
    __tablename__ = "holiday_swap_requests"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer,
                              ForeignKey("employees.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    holiday_date    = Column(Date, nullable=False)   # date they want to work
    work_date       = Column(Date, nullable=False)   # date they want to take off
    reason          = Column(Text, nullable=False)
    status          = Column(SAEnum(SwapStatusEnum),
                              default=SwapStatusEnum.pending, index=True)

    # Approval workflow
    approval_workflow = Column(JSONB, default=[
        {"level": 1, "approver": "Manager", "status": "pending", "required": True},
        {"level": 2, "approver": "HR",      "status": "pending", "required": True},
    ])

    # Decision
    approved_at     = Column(DateTime(timezone=True), nullable=True)
    approved_by     = Column(String(100), nullable=True)
    rejected_at     = Column(DateTime(timezone=True), nullable=True)
    rejected_by     = Column(String(100), nullable=True)

    submitted_at    = Column(DateTime(timezone=True), server_default=func.now())
    updated_at      = Column(DateTime(timezone=True), server_default=func.now(),
                              onupdate=func.now())

    employee        = relationship("Employee", back_populates="holiday_swap_requests")

    __table_args__ = (
        Index("ix_hc_swap_status",       "status"),
        Index("ix_swap_holiday_date", "holiday_date"),
    )

    def __repr__(self):
        return (
            f"<HolidaySwapRequest emp={self.employee_id} "
            f"holiday={self.holiday_date} work={self.work_date} [{self.status}]>"
        )


# ─────────────────────────────────────────────────────────
# TAB 5 — HOLIDAY CARRY FORWARD
# ─────────────────────────────────────────────────────────

class HolidayCarryForward(Base):
    __tablename__ = "holiday_carry_forwards"

    id              = Column(Integer, primary_key=True, index=True)
    employee_id     = Column(Integer,
                              ForeignKey("employees.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    from_year       = Column(Integer, nullable=False)
    to_year         = Column(Integer, nullable=False)
    holidays        = Column(JSONB, default=[])   # list of holiday IDs
    holiday_count   = Column(Integer, default=0)  # len(holidays)
    status          = Column(SAEnum(CarryForwardStatusEnum),
                              default=CarryForwardStatusEnum.processed)
    processed_at    = Column(DateTime(timezone=True), server_default=func.now())
    processed_by    = Column(Integer, nullable=True)
    processed_by_name = Column(String(100), default="HR Admin")

    employee        = relationship("Employee", back_populates="holiday_carry_forwards")

    __table_args__ = (
        Index("ix_cf_employee", "employee_id"),
        Index("ix_cf_years",    "from_year", "to_year"),
    )

    def __repr__(self):
        return (
            f"<HolidayCarryForward emp={self.employee_id} "
            f"{self.from_year}→{self.to_year} [{self.holiday_count} holidays]>"
        )
