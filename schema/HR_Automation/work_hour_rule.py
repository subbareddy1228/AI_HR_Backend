"""
schemas/work_hour_rules_schema.py
Pydantic v2 schemas exactly matching the initialState shape from WorkHourRules.jsx.
Every field name uses camelCase to match the frontend JSON keys.
"""

from __future__ import annotations
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


# ═══════════════════════════════════════════════════════════
# TAB 1 — ATTENDANCE RULES
# ═══════════════════════════════════════════════════════════

class LateArrival(BaseModel):
    enabled:          bool  = True
    gracePeriod:      int   = 15          # minutes
    deductionType:    str   = "perMinute" # perMinute | perHour | fixed | leave | warning
    deductionAmount:  float = 10.0
    monthlyLimit:     int   = 120         # minutes
    maxAllowed:       int   = 5           # instances/month
    autoDeduct:       bool  = True


class EarlyDeparture(BaseModel):
    allowed:         bool  = True
    penaltyType:     str   = "salaryDeduction"  # salaryDeduction | leaveDeduction | warning | both | none
    penaltyAmount:   float = 100.0
    gracePeriod:     int   = 10
    requireApproval: bool  = True
    maxInstances:    int   = 3


class HalfDayCriteria(BaseModel):
    hours:              float = 4.0
    considerAsHalfDay:  bool  = True
    markAsAbsentBelow:  bool  = True
    applyAfterHours:    float = 3.0
    autoDeduct:         bool  = True


class ShortLeaveCategory(BaseModel):
    id:           Optional[int] = None    # assigned server-side on create
    name:         str
    maxDuration:  float         = 2.0     # hours
    requiresDoc:  bool          = False
    icon:         str           = "bi-clock"
    color:        str           = "secondary"


class ShortLeave(BaseModel):
    maxDuration:       float                  = 2.0
    maxFrequency:      int                    = 4
    requiresApproval:  bool                   = True
    autoDeduct:        bool                   = False
    categories:        List[ShortLeaveCategory] = Field(default_factory=list)


class ContinuousAbsence(BaseModel):
    threshold:        int       = 3
    escalationLevels: List[str] = Field(default=["Manager", "HR", "Director", "CEO"])
    notifyAfterDays:  int       = 2
    currentLevel:     str       = "Manager"
    autoAlert:        bool      = True
    emailAlerts:      bool      = True
    smsAlerts:        bool      = False


class WeekendWorking(BaseModel):
    requiresApproval:  bool  = True
    rate:              float = 1.5
    maxHours:          int   = 8
    advanceNotice:     int   = 48   # hours
    compOffAllowed:    bool  = True
    compOffValidity:   int   = 30   # days


class HolidayWorking(BaseModel):
    requiresApproval: bool  = True
    rate:             float = 2.0
    canTakeCompOff:   bool  = True
    compOffValidity:  int   = 60
    advanceApproval:  bool  = True
    mandatoryRate:    float = 2.5


class WorkFromHome(BaseModel):
    allowed:           bool = True
    maxDaysPerWeek:    int  = 2
    requireApproval:   bool = True
    trackProductivity: bool = True


class AttendanceRules(BaseModel):
    lateArrival:       LateArrival       = Field(default_factory=LateArrival)
    earlyDeparture:    EarlyDeparture    = Field(default_factory=EarlyDeparture)
    minWorkHours:      float             = 8.0
    halfDayCriteria:   HalfDayCriteria   = Field(default_factory=HalfDayCriteria)
    shortLeave:        ShortLeave        = Field(default_factory=ShortLeave)
    continuousAbsence: ContinuousAbsence = Field(default_factory=ContinuousAbsence)
    weekendWorking:    WeekendWorking     = Field(default_factory=WeekendWorking)
    holidayWorking:    HolidayWorking     = Field(default_factory=HolidayWorking)
    workFromHome:      WorkFromHome       = Field(default_factory=WorkFromHome)


# ═══════════════════════════════════════════════════════════
# TAB 2 — OVERTIME MANAGEMENT
# ═══════════════════════════════════════════════════════════

class OTEligibility(BaseModel):
    minWorkHours:    float       = 8.0
    excludeWeekends: bool        = False
    employeeLevels:  List[str]   = Field(default=["permanent", "contract"])
    departments:     List[str]   = Field(default=["all"])
    probationPeriod: int         = 90   # days
    includeWFH:      bool        = False


class OTCalculation(BaseModel):
    method:          str   = "multiplier"   # multiplier | fixed
    weekdayRate:     float = 1.5
    weekendRate:     float = 2.0
    holidayRate:     float = 3.0
    fixedRate:       float = 0.0
    nightShiftBonus: float = 0.25
    roundToNearest:  float = 0.25


class OTApprovalWorkflow(BaseModel):
    levels:               List[str] = Field(default=["Manager", "HR"])
    autoApproveAfter:     int       = 24    # hours
    requireDocumentation: bool      = True
    maxApprovalDays:      int       = 7
    notifyIfPending:      bool      = True
    escalationAfterHours: int       = 48


class OTCaps(BaseModel):
    daily:           float = 4.0
    weekly:          float = 20.0
    monthly:         float = 48.0
    quarterly:       float = 120.0
    yearly:          float = 480.0
    consecutiveDays: int   = 5


class OTCompensation(BaseModel):
    type:                 str   = "pay"        # pay | compOff | both
    compOffValidity:      int   = 90           # days
    autoConvertToCompOff: bool  = False
    conversionRate:       float = 1.0
    paymentCycle:         str   = "monthly"
    taxDeductible:        bool  = True


class OvertimeCategory(BaseModel):
    id:               Optional[int] = None
    name:             str
    rate:             float = 1.5
    caps:             Dict[str, float] = Field(default={"daily": 3.0, "weekly": 10.0})
    requiresApproval: bool  = True


class OvertimeRules(BaseModel):
    eligibility:      OTEligibility      = Field(default_factory=OTEligibility)
    calculation:      OTCalculation      = Field(default_factory=OTCalculation)
    approvalWorkflow: OTApprovalWorkflow = Field(default_factory=OTApprovalWorkflow)
    caps:             OTCaps             = Field(default_factory=OTCaps)
    compensation:     OTCompensation     = Field(default_factory=OTCompensation)
    categories:       List[OvertimeCategory] = Field(default_factory=list)


# ═══════════════════════════════════════════════════════════
# TAB 3 — BREAK MANAGEMENT
# ═══════════════════════════════════════════════════════════

class BreakItem(BaseModel):
    id:             Optional[int] = None
    name:           str
    type:           str   = "unpaid"    # paid | unpaid
    duration:       int   = 60          # minutes
    autoDeduct:     bool  = True
    mandatory:      bool  = True
    windowStart:    str   = "12:00"     # HH:MM
    windowEnd:      str   = "14:00"
    flexibleWindow: int   = 30          # minutes of flex around window
    maxDelay:       int   = 15          # max minutes late before penalty
    minGapAfter:    int   = 180         # min minutes before next break allowed


class BreakEnforcement(BaseModel):
    strictMode:          bool = False
    allowMultipleBreaks: bool = True
    maxBreaksPerDay:     int  = 4
    trackBreakPunches:   bool = True
    deductFromWorkHours: bool = True
    enforceSequence:     bool = False
    autoLogBreaks:       bool = True
    breakReminders:      bool = True
    reminderBefore:      int  = 5    # minutes before break window


class BreakPolicies(BaseModel):
    minBreakDuration:           int   = 5
    maxBreakDuration:           int   = 120
    totalBreakLimit:            int   = 90
    mealBreakRequired:          bool  = True
    mealBreakAfterHours:        float = 5.0
    consecutiveWorkLimit:       float = 4.0
    mandatoryRestAfterOvertime: int   = 11    # hours


class BreakRules(BaseModel):
    breaks:      List[BreakItem]   = Field(default_factory=list)
    enforcement: BreakEnforcement  = Field(default_factory=BreakEnforcement)
    policies:    BreakPolicies     = Field(default_factory=BreakPolicies)


# ═══════════════════════════════════════════════════════════
# TAB 4 — SETTINGS
# ═══════════════════════════════════════════════════════════

class WorkHourSettingsIn(BaseModel):
    currency:           Optional[str]  = None   # USD | EUR | GBP | INR
    timeFormat:         Optional[str]  = None   # 12h | 24h
    dateFormat:         Optional[str]  = None   # DD/MM/YYYY | MM/DD/YYYY
    weekStart:          Optional[str]  = None   # Monday | Sunday
    fiscalYearStart:    Optional[str]  = None   # April | January | …
    autoSave:           Optional[bool] = None
    backupFrequency:    Optional[str]  = None   # daily | Weekly | Monthly
    notificationEmails: Optional[bool] = None
    smsAlerts:          Optional[bool] = None


class WorkHourSettingsOut(BaseModel):
    currency:           str  = "INR"
    timeFormat:         str  = "24h"
    dateFormat:         str  = "DD/MM/YYYY"
    weekStart:          str  = "Monday"
    fiscalYearStart:    str  = "April"
    autoSave:           bool = True
    backupFrequency:    str  = "daily"
    notificationEmails: bool = True
    smsAlerts:          bool = False
    lastBackupAt:       Optional[datetime] = None
    rulesVersion:       str  = "v3.2.1"

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# COMPLIANCE STATS  (header stat bar)
# ═══════════════════════════════════════════════════════════

class ComplianceStatsOut(BaseModel):
    """
    6 stat cards shown below the header:
    Active Rules · Grace Period · Min Hours · Short Leave · Absence Alert · Weekend Rate
    + Compliance Score badge (computed dynamically)
    """
    activeRules:              int   # count of enabled rule sections
    gracePeriodMinutes:       int   # lateArrival.gracePeriod
    minHours:                 float # attendanceRules.minWorkHours
    shortLeaveCategories:     int   # shortLeave.categories.length
    absenceAlertDays:         int   # continuousAbsence.threshold  (shown as "3d")
    weekendRate:              float # weekendWorking.rate           (shown as "1.5x")
    complianceScore:          int   # computed: 100 + 10 per active sub-rule


# ═══════════════════════════════════════════════════════════
# FULL CONFIG  (page load / save response)
# ═══════════════════════════════════════════════════════════

class WorkHourRuleConfigOut(BaseModel):
    attendance_rules: Dict[str, Any]
    overtime_rules:   Dict[str, Any]
    break_rules:      Dict[str, Any]
    settings:         Dict[str, Any]
    last_backup_at:   Optional[datetime] = None
    updated_at:       Optional[datetime] = None

    model_config = {"from_attributes": True}


# ═══════════════════════════════════════════════════════════
# SAVE PAYLOADS
# ═══════════════════════════════════════════════════════════

class SaveAllIn(BaseModel):
    """Save Changes button — any tab may be omitted (partial update)."""
    attendance_rules: Optional[Dict[str, Any]] = None
    overtime_rules:   Optional[Dict[str, Any]] = None
    break_rules:      Optional[Dict[str, Any]] = None
    settings:         Optional[Dict[str, Any]] = None


class SaveTabIn(BaseModel):
    """Auto-save single tab payload."""
    tab:  str            # "attendance" | "overtime" | "breaks" | "settings"
    data: Dict[str, Any]


# ═══════════════════════════════════════════════════════════
# RESET RESPONSE
# ═══════════════════════════════════════════════════════════

class ResetOut(BaseModel):
    message:          str
    reset_tab:        Optional[str] = None   # None = all tabs
    config:           WorkHourRuleConfigOut


# ═══════════════════════════════════════════════════════════
# GENERIC
# ═══════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    message: str
