"""
services/work_hour_rules_service.py
Business logic for all 4 tabs of Work Hour Rules & Policies.
"""

from __future__ import annotations
import copy
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from model.HR_Automation.work_hour_rule import WorkHourRuleConfig

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# DEFAULT STATE  (mirrors initialState from WorkHourRules.jsx)
# ─────────────────────────────────────────────────────────

DEFAULT_ATTENDANCE_RULES: Dict[str, Any] = {
    "lateArrival": {
        "enabled": True,
        "gracePeriod": 15,
        "deductionType": "perMinute",
        "deductionAmount": 10,
        "monthlyLimit": 120,
        "maxAllowed": 5,
        "autoDeduct": True,
    },
    "earlyDeparture": {
        "allowed": True,
        "penaltyType": "salaryDeduction",
        "penaltyAmount": 100,
        "gracePeriod": 10,
        "requireApproval": True,
        "maxInstances": 3,
    },
    "minWorkHours": 8,
    "halfDayCriteria": {
        "hours": 4,
        "considerAsHalfDay": True,
        "markAsAbsentBelow": True,
        "applyAfterHours": 3,
        "autoDeduct": True,
    },
    "shortLeave": {
        "maxDuration": 2,
        "maxFrequency": 4,
        "requiresApproval": True,
        "autoDeduct": False,
        "categories": [
            {"id": 1, "name": "Medical",   "maxDuration": 4, "requiresDoc": True,  "icon": "bi-heart-pulse",            "color": "danger"},
            {"id": 2, "name": "Personal",  "maxDuration": 2, "requiresDoc": False, "icon": "bi-person",                 "color": "primary"},
            {"id": 3, "name": "Family",    "maxDuration": 3, "requiresDoc": False, "icon": "bi-people-fill",            "color": "success"},
            {"id": 4, "name": "Emergency", "maxDuration": 6, "requiresDoc": True,  "icon": "bi-exclamation-triangle",   "color": "warning"},
        ],
    },
    "continuousAbsence": {
        "threshold": 3,
        "escalationLevels": ["Manager", "HR", "Director", "CEO"],
        "notifyAfterDays": 2,
        "currentLevel": "Manager",
        "autoAlert": True,
        "emailAlerts": True,
        "smsAlerts": False,
    },
    "weekendWorking": {
        "requiresApproval": True,
        "rate": 1.5,
        "maxHours": 8,
        "advanceNotice": 48,
        "compOffAllowed": True,
        "compOffValidity": 30,
    },
    "holidayWorking": {
        "requiresApproval": True,
        "rate": 2.0,
        "canTakeCompOff": True,
        "compOffValidity": 60,
        "advanceApproval": True,
        "mandatoryRate": 2.5,
    },
    "workFromHome": {
        "allowed": True,
        "maxDaysPerWeek": 2,
        "requireApproval": True,
        "trackProductivity": True,
    },
}

DEFAULT_OVERTIME_RULES: Dict[str, Any] = {
    "eligibility": {
        "minWorkHours": 8,
        "excludeWeekends": False,
        "employeeLevels": ["permanent", "contract"],
        "departments": ["all"],
        "probationPeriod": 90,
        "includeWFH": False,
    },
    "calculation": {
        "method": "multiplier",
        "weekdayRate": 1.5,
        "weekendRate": 2.0,
        "holidayRate": 3.0,
        "fixedRate": 0,
        "nightShiftBonus": 0.25,
        "roundToNearest": 0.25,
    },
    "approvalWorkflow": {
        "levels": ["Manager", "HR"],
        "autoApproveAfter": 24,
        "requireDocumentation": True,
        "maxApprovalDays": 7,
        "notifyIfPending": True,
        "escalationAfterHours": 48,
    },
    "caps": {
        "daily": 4,
        "weekly": 20,
        "monthly": 48,
        "quarterly": 120,
        "yearly": 480,
        "consecutiveDays": 5,
    },
    "compensation": {
        "type": "pay",
        "compOffValidity": 90,
        "autoConvertToCompOff": False,
        "conversionRate": 1.0,
        "paymentCycle": "monthly",
        "taxDeductible": True,
    },
    "categories": [
        {"id": 1, "name": "Regular Overtime",   "rate": 1.5, "caps": {"daily": 3, "weekly": 10}, "requiresApproval": True},
        {"id": 2, "name": "Emergency Overtime",  "rate": 2.0, "caps": {"daily": 4, "weekly": 16}, "requiresApproval": False},
    ],
}

DEFAULT_BREAK_RULES: Dict[str, Any] = {
    "breaks": [
        {
            "id": 1, "name": "Lunch Break", "type": "unpaid",
            "duration": 60, "autoDeduct": True,  "mandatory": True,
            "windowStart": "12:00", "windowEnd": "14:00",
            "flexibleWindow": 30, "maxDelay": 15, "minGapAfter": 180,
        },
        {
            "id": 2, "name": "Tea Break",   "type": "paid",
            "duration": 15, "autoDeduct": False, "mandatory": False,
            "windowStart": "15:30", "windowEnd": "16:00",
            "flexibleWindow": 60, "maxDelay": 30, "minGapAfter": 120,
        },
        {
            "id": 3, "name": "Evening Break", "type": "paid",
            "duration": 10, "autoDeduct": False, "mandatory": False,
            "windowStart": "17:00", "windowEnd": "17:30",
            "flexibleWindow": 45, "maxDelay": 20, "minGapAfter": 90,
        },
    ],
    "enforcement": {
        "strictMode": False,
        "allowMultipleBreaks": True,
        "maxBreaksPerDay": 4,
        "trackBreakPunches": True,
        "deductFromWorkHours": True,
        "enforceSequence": False,
        "autoLogBreaks": True,
        "breakReminders": True,
        "reminderBefore": 5,
    },
    "policies": {
        "minBreakDuration": 5,
        "maxBreakDuration": 120,
        "totalBreakLimit": 90,
        "mealBreakRequired": True,
        "mealBreakAfterHours": 5,
        "consecutiveWorkLimit": 4,
        "mandatoryRestAfterOvertime": 11,
    },
}

DEFAULT_SETTINGS: Dict[str, Any] = {
    "currency":           "INR",
    "timeFormat":         "24h",
    "dateFormat":         "DD/MM/YYYY",
    "weekStart":          "Monday",
    "fiscalYearStart":    "April",
    "autoSave":           True,
    "backupFrequency":    "daily",
    "notificationEmails": True,
    "smsAlerts":          False,
}

TAB_COLUMN_MAP = {
    "attendance": "attendance_rules",
    "overtime":   "overtime_rules",
    "breaks":     "break_rules",
    "settings":   "settings",
}


# ═══════════════════════════════════════════════════════════
# HELPERS
# ═══════════════════════════════════════════════════════════

def _get_or_create(db: Session) -> WorkHourRuleConfig:
    config = db.query(WorkHourRuleConfig).filter_by(id=1).first()
    if not config:
        config = WorkHourRuleConfig(
            id=1,
            attendance_rules=copy.deepcopy(DEFAULT_ATTENDANCE_RULES),
            overtime_rules=copy.deepcopy(DEFAULT_OVERTIME_RULES),
            break_rules=copy.deepcopy(DEFAULT_BREAK_RULES),
            settings=copy.deepcopy(DEFAULT_SETTINGS),
        )
        db.add(config)
        db.commit()
        db.refresh(config)
    return config


def _to_out(config: WorkHourRuleConfig) -> dict:
    return {
        "attendance_rules": config.attendance_rules or {},
        "overtime_rules":   config.overtime_rules   or {},
        "break_rules":      config.break_rules       or {},
        "settings":         config.settings          or {},
        "last_backup_at":   config.last_backup_at,
        "updated_at":       config.updated_at,
    }


def _deep_merge(base: dict, update: dict) -> dict:
    """Recursively merge update into base (non-destructive for unmentioned keys)."""
    result = copy.deepcopy(base)
    for k, v in update.items():
        if isinstance(v, dict) and isinstance(result.get(k), dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result


# ═══════════════════════════════════════════════════════════
# SERVICE FUNCTIONS
# ═══════════════════════════════════════════════════════════

def get_config(db: Session) -> dict:
    """Page load — seed defaults on first call."""
    return _to_out(_get_or_create(db))


def get_compliance_stats(db: Session) -> dict:
    """
    Computes the 6 stat card values + compliance score dynamically.

    Score formula (matches what the frontend considers "active"):
      base = 100
      +10 for each of: lateArrival.enabled, earlyDeparture.allowed,
           minWorkHours > 0, shortLeave.requiresApproval,
           continuousAbsence.autoAlert, weekendWorking.requiresApproval,
           holidayWorking.requiresApproval  (7 possible sub-rules)
    """
    config = _get_or_create(db)
    att = config.attendance_rules or {}
    ot  = config.overtime_rules   or {}

    la  = att.get("lateArrival",       {})
    ed  = att.get("earlyDeparture",    {})
    sl  = att.get("shortLeave",        {})
    ca  = att.get("continuousAbsence", {})
    ww  = att.get("weekendWorking",    {})
    hw  = att.get("holidayWorking",    {})
    mwh = att.get("minWorkHours",      0)

    active_count = sum([
        bool(la.get("enabled",           False)),
        bool(ed.get("allowed",           False)),
        bool(mwh),
        bool(sl.get("requiresApproval",  False)),
        bool(ca.get("autoAlert",         False)),
        bool(ww.get("requiresApproval",  False)),
        bool(hw.get("requiresApproval",  False)),
    ])

    return {
        "activeRules":          active_count,
        "gracePeriodMinutes":   la.get("gracePeriod",          15),
        "minHours":             float(mwh) if mwh else 8.0,
        "shortLeaveCategories": len(sl.get("categories", [])),
        "absenceAlertDays":     ca.get("threshold",            3),
        "weekendRate":          ww.get("rate",                 1.5),
        "complianceScore":      100 + (active_count * 10),
    }


def save_all(
    db: Session,
    attendance_rules: Optional[dict],
    overtime_rules:   Optional[dict],
    break_rules:      Optional[dict],
    settings:         Optional[dict],
    saved_by:         Optional[int] = None,
) -> dict:
    """Save Changes button — partial update across all 4 tabs."""
    config = _get_or_create(db)

    if attendance_rules is not None:
        config.attendance_rules = _deep_merge(
            config.attendance_rules or {}, attendance_rules
        )
    if overtime_rules is not None:
        config.overtime_rules = _deep_merge(
            config.overtime_rules or {}, overtime_rules
        )
    if break_rules is not None:
        config.break_rules = _deep_merge(
            config.break_rules or {}, break_rules
        )
    if settings is not None:
        config.settings = _deep_merge(
            config.settings or {}, settings
        )

    config.updated_by = saved_by
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    logger.info("Work hour rules saved by user %s", saved_by)
    return _to_out(config)


def save_tab(
    db: Session,
    tab: str,
    data: dict,
    saved_by: Optional[int] = None,
) -> dict:
    """Auto-save single tab (attendance | overtime | breaks | settings)."""
    col = TAB_COLUMN_MAP.get(tab)
    if not col:
        raise ValueError(f"Unknown tab '{tab}'.")

    config = _get_or_create(db)
    current = getattr(config, col) or {}
    setattr(config, col, _deep_merge(current, data))
    config.updated_by = saved_by
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    return _to_out(config)


def reset_config(
    db: Session,
    tab: Optional[str] = None,
    reset_by: Optional[int] = None,
) -> dict:
    """Reset one tab or all tabs to defaults."""
    config = _get_or_create(db)

    if tab is None:
        config.attendance_rules = copy.deepcopy(DEFAULT_ATTENDANCE_RULES)
        config.overtime_rules   = copy.deepcopy(DEFAULT_OVERTIME_RULES)
        config.break_rules      = copy.deepcopy(DEFAULT_BREAK_RULES)
        config.settings         = copy.deepcopy(DEFAULT_SETTINGS)
        reset_label = "all tabs"
    else:
        defaults = {
            "attendance": ("attendance_rules", DEFAULT_ATTENDANCE_RULES),
            "overtime":   ("overtime_rules",   DEFAULT_OVERTIME_RULES),
            "breaks":     ("break_rules",      DEFAULT_BREAK_RULES),
            "settings":   ("settings",         DEFAULT_SETTINGS),
        }
        col, default = defaults[tab]
        setattr(config, col, copy.deepcopy(default))
        reset_label = tab

    config.updated_by = reset_by
    config.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)

    return {
        "message":   f"Reset to defaults: {reset_label}.",
        "reset_tab": tab,
        "config":    _to_out(config),
    }


def export_config(db: Session) -> dict:
    """Export button — returns full config as a plain dict for JSON download."""
    config = _get_or_create(db)
    return {
        "attendance_rules": config.attendance_rules or {},
        "overtime_rules":   config.overtime_rules   or {},
        "break_rules":      config.break_rules       or {},
        "settings":         config.settings          or {},
        "exported_at":      datetime.now(timezone.utc).isoformat(),
        "version":          "v3.2.1",
    }


def import_config(
    db: Session,
    data: dict,
    imported_by: Optional[int] = None,
) -> dict:
    """Import button — overwrites all tabs from uploaded JSON."""
    config = _get_or_create(db)
    config.attendance_rules = data.get("attendance_rules",
                                        config.attendance_rules or {})
    config.overtime_rules   = data.get("overtime_rules",
                                        config.overtime_rules   or {})
    config.break_rules      = data.get("break_rules",
                                        config.break_rules       or {})
    config.settings         = data.get("settings",
                                        config.settings          or {})
    config.updated_by       = imported_by
    config.updated_at       = datetime.now(timezone.utc)
    db.commit()
    db.refresh(config)
    logger.info("Work hour rules imported by user %s", imported_by)
    return _to_out(config)
