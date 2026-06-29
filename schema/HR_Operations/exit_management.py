# schema/HR_Operations/exit_management.py
# Pydantic schemas for Exit Management & Clearance (all 5 tabs)

from pydantic import BaseModel, ConfigDict
from datetime import date, datetime
from typing import Optional, List
from decimal import Decimal


# ─────────────────────────────────────────────────────────────────────────────
#  Shared embedded employee info
# ─────────────────────────────────────────────────────────────────────────────
class EmployeeBasic(BaseModel):
    id:             int
    first_name:     str
    last_name:      Optional[str] = None
    employee_code:  Optional[str] = None
    designation:    Optional[str] = None
    department:     Optional[str] = None
    location:       Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 1  —  EXIT CASES  (core exit record)
# ═════════════════════════════════════════════════════════════════════════════

class ExitManagementCreate(BaseModel):
    employee_id:      int
    resignation_date: date
    last_working_date: Optional[date] = None
    # exit_type: Resignation | Termination | Retirement | Absconding | Better Opportunity
    exit_type:        str
    reason:           Optional[str] = None
    remarks:          Optional[str] = None


class ExitManagementUpdate(BaseModel):
    last_working_date:   Optional[date] = None
    # Status: In Progress | Pending | Completed | Escalated | Cancelled
    status:              Optional[str]  = None
    exit_type:           Optional[str]  = None
    clearance_progress:  Optional[int]  = None   # 0-100
    pending_items:       Optional[int]  = None
    # Clearance checklist
    it_clearance:        Optional[bool] = None
    finance_clearance:   Optional[bool] = None
    hr_clearance:        Optional[bool] = None
    admin_clearance:     Optional[bool] = None
    assets_returned:     Optional[bool] = None
    exit_interview_done: Optional[bool] = None
    knowledge_transfer:  Optional[bool] = None
    reason:              Optional[str]  = None
    remarks:             Optional[str]  = None


class ExitManagementResponse(BaseModel):
    id:                  int
    employee_id:         int
    employee:            Optional[EmployeeBasic] = None
    resignation_date:    date
    last_working_date:   Optional[date]
    days_left:           Optional[int]            # computed live
    exit_type:           str
    status:              str
    clearance_progress:  int
    pending_items:       int
    it_clearance:        bool
    finance_clearance:   bool
    hr_clearance:        bool
    admin_clearance:     bool
    assets_returned:     bool
    exit_interview_done: bool
    knowledge_transfer:  bool
    reason:              Optional[str]
    remarks:             Optional[str]
    created_at:          datetime
    updated_at:          datetime

    model_config = ConfigDict(from_attributes=True)


# ── Dashboard stat cards ──────────────────────────────────────────────────────
class ExitDashboard(BaseModel):
    total_cases:  int
    pending:      int
    escalated:    int
    alumni:       int


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 2  —  ALUMNI
# ═════════════════════════════════════════════════════════════════════════════

class AlumniCreate(BaseModel):
    exit_id:         int
    employee_id:     int
    exit_date:       Optional[date]  = None
    rehire_eligible: Optional[bool]  = False
    boomerang:       Optional[bool]  = False
    # Engagement: High | Medium | Low
    engagement:      Optional[str]   = "Medium"
    remarks:         Optional[str]   = None


class AlumniUpdate(BaseModel):
    rehire_eligible: Optional[bool] = None
    boomerang:       Optional[bool] = None
    engagement:      Optional[str]  = None   # High | Medium | Low
    remarks:         Optional[str]  = None


class AlumniResponse(BaseModel):
    id:              int
    exit_id:         int
    employee_id:     int
    employee:        Optional[EmployeeBasic] = None
    alumni_code:     Optional[str]
    exit_date:       Optional[date]
    rehire_eligible: bool
    boomerang:       bool
    engagement:      Optional[str]
    remarks:         Optional[str]
    created_at:      datetime
    updated_at:      datetime

    model_config = ConfigDict(from_attributes=True)


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 3  —  SETTLEMENTS
# ═════════════════════════════════════════════════════════════════════════════

class SettlementCreate(BaseModel):
    exit_id:          int
    employee_id:      int
    amount:           Decimal
    settlement_date:  Optional[date] = None
    remarks:          Optional[str]  = None


class SettlementUpdate(BaseModel):
    amount:           Optional[Decimal] = None
    settlement_date:  Optional[date]    = None
    # Status: Completed | In Progress | Pending
    status:           Optional[str]     = None
    remarks:          Optional[str]     = None


class SettlementResponse(BaseModel):
    id:               int
    exit_id:          int
    employee_id:      int
    employee:         Optional[EmployeeBasic] = None
    amount:           Decimal
    settlement_date:  Optional[date]
    status:           str
    remarks:          Optional[str]
    created_at:       datetime
    updated_at:       datetime

    model_config = ConfigDict(from_attributes=True)


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 4  —  EMPLOYEE EXITS  (filtered report view)
# ═════════════════════════════════════════════════════════════════════════════

class EmployeeExitRecord(BaseModel):
    sn:          int
    employee_id: int
    employee:    Optional[EmployeeBasic] = None
    location:    Optional[str]
    department:  Optional[str]
    designation: Optional[str]
    joining_date: Optional[date]
    exit_date:   Optional[date]
    exit_reason: str     # badge: Resignation | Termination | Retirement | Better Opportunity

    model_config = ConfigDict(from_attributes=True)


# ═════════════════════════════════════════════════════════════════════════════
#  TAB 5  —  TRENDS  (Exit Trend Analysis modal)
# ═════════════════════════════════════════════════════════════════════════════

class ExitTrendResponse(BaseModel):
    analysis_period:    str           # Last 3 Months | Last 6 Months | Last 1 Year
    department:         Optional[str]
    exit_rate_pct:      float         # 12.5%
    avg_tenure_years:   float         # 2.8 yrs
    top_exit_reason:    str           # Better Opportunity
    total_exits:        int
    by_reason:          dict          # {"Resignation": 5, "Termination": 2, ...}
    by_department:      dict          # {"Engineering": 3, ...}


# ── Filter options for dropdowns ──────────────────────────────────────────────
class ExitFilterOptions(BaseModel):
    locations:    List[str]
    departments:  List[str]
    exit_reasons: List[str]
    statuses:     List[str]
