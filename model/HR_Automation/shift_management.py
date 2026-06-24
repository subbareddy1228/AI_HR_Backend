"""
models/shift_management.py
SQLAlchemy ORM models for Shift Management & Rostering module.

Covers all 6 tabs:
  Tab 1 — Shift Master      : ShiftMaster, ShiftBreakTime
  Tab 2 — Shift Assignment  : ShiftAssignment
  Tab 3 — Rostering         : ShiftRoster, ShiftRosterDay
  Tab 4 — Shift Swap        : ShiftSwapRequest
  Tab 5 — Flexible Work     : FlexibleArrangement
  Tab 6 — Work Hour Rules   : WorkHourRules (singleton JSON config)
"""

import uuid
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, DateTime, Date, Time,
    ForeignKey, Text, Numeric, Enum as SAEnum, Index, UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from core.database import Base


# ─────────────────────────────────────────────────────────
# ENUMS
# ─────────────────────────────────────────────────────────

class ShiftTypeEnum(str, enum.Enum):
    general    = "general"
    night      = "night"
    rotational = "rotational"
    flexible   = "flexible"


class RotationPatternEnum(str, enum.Enum):
    daily    = "daily"
    weekly   = "weekly"
    biweekly = "biweekly"


class RosterPeriodEnum(str, enum.Enum):
    weekly  = "weekly"
    monthly = "monthly"


class RosterStatusEnum(str, enum.Enum):
    draft     = "draft"
    published = "published"


class SwapStatusEnum(str, enum.Enum):
    pending  = "pending"
    approved = "approved"
    rejected = "rejected"


class ArrangementTypeEnum(str, enum.Enum):
    flexible   = "flexible"
    hybrid     = "hybrid"
    compressed = "compressed"
    remote     = "remote"


class NotificationTypeEnum(str, enum.Enum):
    shift_assigned      = "shift_assigned"
    shift_swapped       = "shift_swapped"
    shift_swap_rejected = "shift_swap_rejected"
    roster_published    = "roster_published"
    shift_changed       = "shift_changed"


# ─────────────────────────────────────────────────────────
# TAB 1 — SHIFT MASTER
# ─────────────────────────────────────────────────────────

class ShiftMaster(Base):
    __tablename__ = "shift_masters"

    id                    = Column(Integer, primary_key=True, index=True)
    name                  = Column(String(100), nullable=False)
    code                  = Column(String(20),  nullable=False, unique=True, index=True)
    shift_type            = Column(SAEnum(ShiftTypeEnum), nullable=False, default=ShiftTypeEnum.general)
    start_time            = Column(String(5), nullable=False)    # "HH:MM"
    end_time              = Column(String(5), nullable=False)    # "HH:MM"
    duration_hours        = Column(Float,    nullable=False, default=8.0)
    grace_period_minutes  = Column(Integer,  default=15)
    week_offs             = Column(JSONB,    default=[])         # ["Sunday"]
    differential_pay      = Column(Float,    default=1.0)        # 1x / 1.25x / 2x
    is_active             = Column(Boolean,  default=True)
    description           = Column(Text,     default="")
    allow_multiple_per_day= Column(Boolean,  default=False)

    # Flexible shift only
    core_hours_start      = Column(String(5), nullable=True)     # "10:00"
    core_hours_end        = Column(String(5), nullable=True)     # "16:00"

    # Rotational shift only
    rotation_pattern      = Column(SAEnum(RotationPatternEnum), nullable=True)

    created_at            = Column(DateTime(timezone=True), server_default=func.now())
    updated_at            = Column(DateTime(timezone=True), server_default=func.now(),
                                   onupdate=func.now())
    created_by            = Column(Integer, nullable=True)

    # Relationships
    break_times           = relationship("ShiftBreakTime", back_populates="shift",
                                         cascade="all, delete-orphan")
    assignments           = relationship("ShiftAssignment",    back_populates="shift")
    roster_days           = relationship("ShiftRosterDay",     back_populates="shift")

    __table_args__ = (
        Index("ix_shift_type",   "shift_type"),
        Index("ix_shift_active", "is_active"),
    )

    def __repr__(self):
        return f"<ShiftMaster {self.code} {self.name} [{self.shift_type}]>"


class ShiftBreakTime(Base):
    """Break times nested inside a shift — shown in Add Shift modal."""
    __tablename__ = "shift_break_times"

    id         = Column(Integer, primary_key=True, index=True)
    shift_id   = Column(Integer, ForeignKey("shift_masters.id", ondelete="CASCADE"), nullable=False)
    name       = Column(String(50), default="Break")
    start_time = Column(String(5), nullable=False)   # "13:00"
    end_time   = Column(String(5), nullable=False)   # "14:00"
    duration   = Column(Integer,   default=60)        # minutes
    is_paid    = Column(Boolean,   default=False)
    mandatory  = Column(Boolean,   default=True)
    auto_deduct= Column(Boolean,   default=True)

    shift      = relationship("ShiftMaster", back_populates="break_times")

    __table_args__ = (
        Index("ix_break_shift", "shift_id"),
    )


# ─────────────────────────────────────────────────────────
# TAB 2 — SHIFT ASSIGNMENT
# ─────────────────────────────────────────────────────────

class ShiftAssignment(Base):
    """One row per employee-shift assignment (individual or bulk)."""
    __tablename__ = "shift_assignments"

    id          = Column(Integer, primary_key=True, index=True)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    shift_id    = Column(Integer,  ForeignKey("shift_masters.id", ondelete="CASCADE"),
                         nullable=False)
    start_date  = Column(Date,    nullable=False)
    end_date    = Column(Date,    nullable=True)     # NULL = ongoing
    is_active   = Column(Boolean, default=True)
    assigned_by = Column(Integer, nullable=True)
    assigned_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    employee    = relationship("Employee",    back_populates="shift_assignments")
    shift       = relationship("ShiftMaster", back_populates="assignments")

    __table_args__ = (
        Index("ix_assignment_emp",   "employee_id"),
        Index("ix_assignment_shift", "shift_id"),
        Index("ix_assignment_active","is_active"),
    )

    def __repr__(self):
        return f"<ShiftAssignment emp={self.employee_id} shift={self.shift_id}>"


# ─────────────────────────────────────────────────────────
# TAB 3 — ROSTERING
# ─────────────────────────────────────────────────────────

class ShiftRoster(Base):
    """Header row for a generated roster (weekly or monthly)."""
    __tablename__ = "shift_rosters"

    id               = Column(Integer, primary_key=True, index=True)
    name             = Column(String(200), nullable=False)
    shift_id         = Column(Integer, ForeignKey("shift_masters.id", ondelete="CASCADE"),
                              nullable=False)
    period           = Column(SAEnum(RosterPeriodEnum), nullable=False)
    start_date       = Column(Date, nullable=False)
    end_date         = Column(Date, nullable=False)
    status           = Column(SAEnum(RosterStatusEnum), default=RosterStatusEnum.draft)
    is_published     = Column(Boolean, default=False)
    published_at     = Column(DateTime(timezone=True), nullable=True)
    published_by     = Column(Integer, nullable=True)
    rotation_pattern = Column(SAEnum(RotationPatternEnum), nullable=True)
    rotation_shifts  = Column(JSONB, default=[])    # list of shift IDs involved
    created_at       = Column(DateTime(timezone=True), server_default=func.now())
    created_by       = Column(Integer, nullable=True)

    shift            = relationship("ShiftMaster")
    days             = relationship("ShiftRosterDay", back_populates="roster",
                                    cascade="all, delete-orphan",
                                    order_by="ShiftRosterDay.roster_date")

    __table_args__ = (
        Index("ix_roster_shift",  "shift_id"),
        Index("ix_roster_status", "status"),
    )

    def __repr__(self):
        return f"<ShiftRoster {self.name} {self.start_date}→{self.end_date}>"


class ShiftRosterDay(Base):
    """One day entry inside a roster — holds assigned employees."""
    __tablename__ = "shift_roster_days"

    id               = Column(Integer, primary_key=True, index=True)
    roster_id        = Column(Integer, ForeignKey("shift_rosters.id", ondelete="CASCADE"),
                              nullable=False)
    shift_id         = Column(Integer, ForeignKey("shift_masters.id", ondelete="SET NULL"),
                              nullable=True)
    roster_date      = Column(Date,    nullable=False)
    day_of_week      = Column(String(10), nullable=False)  # "Monday" … "Sunday"
    is_week_off      = Column(Boolean, default=False)
    employees        = Column(JSONB,   default=[])          # list of employee_ids
    rotation_sequence= Column(Integer, nullable=True)       # 1-based sequence for rotational

    roster           = relationship("ShiftRoster",  back_populates="days")
    shift            = relationship("ShiftMaster",  back_populates="roster_days")

    __table_args__ = (
        UniqueConstraint("roster_id", "roster_date", name="uq_roster_day"),
        Index("ix_roster_day_date", "roster_date"),
    )


# ─────────────────────────────────────────────────────────
# TAB 4 — SHIFT SWAP
# ─────────────────────────────────────────────────────────

class ShiftSwapRequest(Base):
    __tablename__ = "shift_swap_requests"

    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"),
                                  nullable=False, index=True)
    current_shift_id    = Column(Integer, ForeignKey("shift_masters.id", ondelete="CASCADE"),
                                  nullable=False)
    requested_shift_id  = Column(Integer, ForeignKey("shift_masters.id", ondelete="CASCADE"),
                                  nullable=False)
    swap_date           = Column(Date,    nullable=False)
    swap_with_employee_id=Column(String(20), nullable=True)   # peer-swap (optional)
    reason              = Column(Text,    default="")
    status              = Column(SAEnum(SwapStatusEnum), default=SwapStatusEnum.pending, index=True)
    requested_at        = Column(DateTime(timezone=True), server_default=func.now())
    approved_by         = Column(Integer, nullable=True)
    approved_at         = Column(DateTime(timezone=True), nullable=True)
    rejected_by         = Column(Integer, nullable=True)
    rejected_at         = Column(DateTime(timezone=True), nullable=True)
    rejection_reason    = Column(Text,    nullable=True)

    current_shift       = relationship("ShiftMaster", foreign_keys=[current_shift_id])
    requested_shift     = relationship("ShiftMaster", foreign_keys=[requested_shift_id])
    employee            = relationship("Employee")

    __table_args__ = (
        Index("ix_sm_swap_status", "status"),
        Index("ix_swap_date",   "swap_date"),
    )

    def __repr__(self):
        return f"<ShiftSwapRequest {self.employee_id} {self.swap_date} [{self.status}]>"


# ─────────────────────────────────────────────────────────
# TAB 5 — FLEXIBLE WORK ARRANGEMENTS
# ─────────────────────────────────────────────────────────

class FlexibleArrangement(Base):
    __tablename__ = "flexible_arrangements"

    id                  = Column(Integer, primary_key=True, index=True)
    employee_id         = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"),
                                  nullable=False, unique=True, index=True)
    arrangement_type    = Column(SAEnum(ArrangementTypeEnum), nullable=False)
    core_hours_start    = Column(String(5), default="10:00")
    core_hours_end      = Column(String(5), default="16:00")
    flexible_start      = Column(String(5), default="08:00")
    flexible_end        = Column(String(5), default="20:00")
    remote_work_days    = Column(JSONB, default=[])          # ["Monday","Wednesday"]

    # Hybrid schedule
    office_days         = Column(JSONB, default=[])
    remote_days         = Column(JSONB, default=[])

    # Compressed week
    compressed_enabled  = Column(Boolean, default=False)
    compressed_work_days= Column(Integer, default=4)
    compressed_hours_per_day = Column(Integer, default=10)

    is_active           = Column(Boolean, default=True)
    created_at          = Column(DateTime(timezone=True), server_default=func.now())
    created_by          = Column(Integer, nullable=True)

    employee            = relationship("Employee")

    def __repr__(self):
        return f"<FlexibleArrangement {self.employee_id} [{self.arrangement_type}]>"


# ─────────────────────────────────────────────────────────
# TAB 6 — WORK HOUR RULES  (singleton row, id=1)
# ─────────────────────────────────────────────────────────

class WorkHourRules(Base):
    """
    Singleton config row for all attendance + overtime + break rules.
    Stored as structured columns matching exactly what the UI edits.
    """
    __tablename__ = "work_hour_rules"

    id                              = Column(Integer, primary_key=True, default=1)

    # ── Late Arrival ──
    late_grace_period_minutes       = Column(Integer,  default=15)
    late_deduction_type             = Column(String(20), default="perMinute")
    late_deduction_amount           = Column(Float,    default=0.5)
    late_enabled                    = Column(Boolean,  default=True)
    late_max_allowed_per_month      = Column(Integer,  default=3)
    late_monthly_limit_minutes      = Column(Integer,  default=30)

    # ── Early Departure ──
    early_departure_allowed         = Column(Boolean,  default=False)
    early_departure_penalty_type    = Column(String(20), default="salaryDeduction")
    early_departure_penalty_amount  = Column(Float,    default=1.0)
    early_departure_requires_approval=Column(Boolean,  default=True)
    early_departure_grace_minutes   = Column(Integer,  default=10)

    # ── Work Hours ──
    min_work_hours                  = Column(Float,    default=8.0)
    half_day_hours                  = Column(Float,    default=4.0)
    half_day_consider               = Column(Boolean,  default=True)
    half_day_apply_after_hours      = Column(Float,    default=5.0)
    absent_below_hours              = Column(Float,    default=3.0)

    # ── Short Leave ──
    short_leave_max_duration_hours  = Column(Float,    default=2.0)
    short_leave_max_frequency       = Column(Integer,  default=2)
    short_leave_requires_approval   = Column(Boolean,  default=True)
    short_leave_auto_deduct         = Column(Boolean,  default=True)

    # ── Continuous Absence ──
    continuous_absence_threshold    = Column(Integer,  default=3)
    continuous_absence_auto_alert   = Column(Boolean,  default=True)
    continuous_absence_notify_after = Column(Integer,  default=2)
    escalation_levels               = Column(JSONB,    default=["Manager","HR","Director"])

    # ── Weekend Working ──
    weekend_requires_approval       = Column(Boolean,  default=True)
    weekend_compensation_type       = Column(String(20), default="extraPay")
    weekend_rate                    = Column(Float,    default=1.5)
    weekend_max_hours               = Column(Integer,  default=8)
    weekend_advance_notice_hours    = Column(Integer,  default=24)

    # ── Holiday Working ──
    holiday_requires_approval       = Column(Boolean,  default=True)
    holiday_compensation_type       = Column(String(20), default="doublePay")
    holiday_rate                    = Column(Float,    default=2.0)
    holiday_can_take_comp_off       = Column(Boolean,  default=True)
    holiday_comp_off_validity_days  = Column(Integer,  default=90)
    holiday_advance_approval        = Column(Boolean,  default=True)

    # ── Overtime ──
    ot_min_work_hours               = Column(Float,    default=8.0)
    ot_exclude_weekends             = Column(Boolean,  default=False)
    ot_probation_period_days        = Column(Integer,  default=90)
    ot_include_wfh                  = Column(Boolean,  default=False)
    ot_method                       = Column(String(20), default="multiplier")
    ot_weekday_rate                 = Column(Float,    default=1.5)
    ot_weekend_rate                 = Column(Float,    default=2.0)
    ot_holiday_rate                 = Column(Float,    default=3.0)
    ot_fixed_rate                   = Column(Float,    default=0.0)
    ot_night_shift_bonus            = Column(Float,    default=0.25)
    ot_round_to_nearest             = Column(Float,    default=0.25)
    ot_approval_levels              = Column(JSONB,    default=["Manager","HR"])
    ot_auto_approve_after_hours     = Column(Integer,  default=24)
    ot_require_documentation        = Column(Boolean,  default=True)
    ot_max_approval_days            = Column(Integer,  default=7)
    ot_cap_daily                    = Column(Float,    default=4.0)
    ot_cap_weekly                   = Column(Float,    default=20.0)
    ot_cap_monthly                  = Column(Float,    default=48.0)
    ot_cap_quarterly                = Column(Float,    default=120.0)
    ot_cap_yearly                   = Column(Float,    default=480.0)
    ot_compensation_type            = Column(String(20), default="pay")
    ot_comp_off_validity_days       = Column(Integer,  default=90)
    ot_auto_convert_to_comp_off     = Column(Boolean,  default=False)
    ot_payment_cycle                = Column(String(20), default="monthly")

    # ── Break Management ──
    break_multiple_allowed          = Column(Boolean,  default=True)
    break_max_duration_minutes      = Column(Integer,  default=120)
    break_punch_required            = Column(Boolean,  default=False)
    break_unpaid_threshold_minutes  = Column(Integer,  default=30)
    break_config                    = Column(JSONB,    default=[])  # list of break dicts

    updated_at  = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    updated_by  = Column(Integer, nullable=True)


# ─────────────────────────────────────────────────────────
# NOTIFICATIONS  (Bell icon panel)
# ─────────────────────────────────────────────────────────

class ShiftNotification(Base):
    __tablename__ = "shift_notifications"

    id          = Column(Integer, primary_key=True, index=True)
    type        = Column(SAEnum(NotificationTypeEnum), nullable=False)
    employee_id = Column(Integer, ForeignKey("employees.id", ondelete="CASCADE"),
                         nullable=False, index=True)
    message     = Column(Text,    nullable=False)
    payload     = Column(JSONB,   default={})    # shift names, dates, roster info
    is_read     = Column(Boolean, default=False)
    created_at  = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    __table_args__ = (
        Index("ix_notif_emp_read", "employee_id", "is_read"),
    )
