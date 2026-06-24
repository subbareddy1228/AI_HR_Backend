"""
models/work_hour_rules.py
Single-row config table storing all 4 tab payloads as JSONB columns.
Mirrors the exact shape of initialState in WorkHourRules.jsx.
"""

from sqlalchemy import Column, Integer, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
from core.database import Base


class WorkHourRuleConfig(Base):
    __tablename__ = "work_hour_rule_configs"

    id = Column(Integer, primary_key=True, default=1)

    # ── Tab 1: Attendance Rules ──────────────────────────────────────────────
    # Stored as one JSONB blob matching attendanceRules shape from the reducer.
    # Top-level keys:
    #   lateArrival, earlyDeparture, minWorkHours, halfDayCriteria,
    #   shortLeave (+ categories[]), continuousAbsence,
    #   weekendWorking, holidayWorking, workFromHome
    attendance_rules = Column(JSONB, nullable=False, default=dict)

    # ── Tab 2: Overtime Management ───────────────────────────────────────────
    # Top-level keys:
    #   eligibility, calculation, approvalWorkflow,
    #   caps, compensation, categories[]
    overtime_rules = Column(JSONB, nullable=False, default=dict)

    # ── Tab 3: Break Management ──────────────────────────────────────────────
    # Top-level keys:
    #   breaks[], enforcement, policies
    break_rules = Column(JSONB, nullable=False, default=dict)

    # ── Tab 4: Settings ──────────────────────────────────────────────────────
    # Fields:
    #   currency, timeFormat, dateFormat, weekStart,
    #   fiscalYearStart, autoSave, backupFrequency,
    #   notificationEmails, smsAlerts
    settings = Column(JSONB, nullable=False, default=dict)

    # ── Backup snapshot (Backup button) ──────────────────────────────────────
    backup_json    = Column(JSONB, nullable=True)
    last_backup_at = Column(DateTime(timezone=True), nullable=True)

    # ── Audit ─────────────────────────────────────────────────────────────────
    updated_at = Column(DateTime(timezone=True), server_default=func.now(),
                        onupdate=func.now())
    updated_by = Column(Integer,
                        nullable=True)

    def __repr__(self):
        return "<WorkHourRuleConfig id=1>"
