"""
schemas/holiday_calendar.py
Pydantic v2 schemas for Holiday Calendar module — all 5 tabs.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, Field, model_validator

from model.HR_Automation.holiday_calendar import (
    HolidayTypeEnum, ApplicationStatusEnum, SwapStatusEnum, CarryForwardStatusEnum,
)


# ══════════════════════════════════════════════════════════
# TAB 1 — HOLIDAY MASTER
# ══════════════════════════════════════════════════════════

class HolidayCreateIn(BaseModel):
    name:               str             = Field(..., max_length=200)
    date:               date
    location:           str             = "All"
    category:           str             = Field(..., description="Public Holiday|National Holiday|Festival|…")
    holidayType:        HolidayTypeEnum = HolidayTypeEnum.gazetted
    optional:           bool            = False
    advanceBookingDays: int             = Field(0, ge=0)
    allowCarryForward:  bool            = False
    carryForwardLimit:  int             = Field(0, ge=0)
    applicableCalendars:List[str]       = ["all"]
    applicableGroups:   List[str]       = ["all"]


class HolidayUpdateIn(BaseModel):
    name:               Optional[str]            = None
    date:               Optional[date]           = None
    location:           Optional[str]            = None
    category:           Optional[str]            = None
    holidayType:        Optional[HolidayTypeEnum]= None
    optional:           Optional[bool]           = None
    advanceBookingDays: Optional[int]            = None
    allowCarryForward:  Optional[bool]           = None
    carryForwardLimit:  Optional[int]            = None
    applicableCalendars:Optional[List[str]]      = None
    applicableGroups:   Optional[List[str]]      = None


class HolidayOut(BaseModel):
    id:                 int
    name:               str
    date:               date
    location:           str
    category:           str
    holidayType:        HolidayTypeEnum
    optional:           bool
    advanceBookingDays: int
    allowCarryForward:  bool
    carryForwardLimit:  int
    applicableCalendars:List[str]
    applicableGroups:   List[str]
    # Display helpers matching table columns
    typeDisplay:        str = ""    # "Mandatory" | "Optional"
    holidayTypeDisplay: str = ""    # "gazetted" badge
    created_at:         datetime

    model_config = {"from_attributes": True}


class HolidayStats(BaseModel):
    totalHolidays:        int
    optionalHolidays:     int
    totalApplications:    int
    pendingApplications:  int
    approvedApplications: int
    rejectedApplications: int


# ══════════════════════════════════════════════════════════
# TAB 2 — OPTIONAL APPLICATIONS
# ══════════════════════════════════════════════════════════

class ApplyOptionalIn(BaseModel):
    """
    Apply Holiday button → Apply Optional Holiday modal.
    Fields: Select Holiday (dropdown of optional=True holidays) · Reason
    """
    holidayId:  int
    employeeId: str
    reason:     str = ""

    @model_validator(mode="after")
    def check_advance_booking(self):
        # Advance booking validation is done server-side using the holiday's
        # advanceBookingDays field
        return self


class UpdateApplicationStatusIn(BaseModel):
    """Update Status modal: Pending | Approved | Rejected"""
    status: ApplicationStatusEnum


class OptionalApplicationOut(BaseModel):
    id:              int
    holiday_id:      int
    employee_id:     str
    employeeName:    str
    holidayName:     str
    holidayDate:     date
    appliedDate:     date
    reason:          str
    status:          ApplicationStatusEnum
    approvalWorkflow:List[dict]
    approvedAt:      Optional[datetime]
    approvedBy:      Optional[str]
    rejectedAt:      Optional[datetime]
    rejectedBy:      Optional[str]
    created_at:      datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# TAB 3 — CALENDARS
# ══════════════════════════════════════════════════════════

class HolidayCalendarCreateIn(BaseModel):
    """
    Add Calendar / Edit Calendar modal.
    Fields: Calendar Name* · Location* · Employee Group · Set as Default
    """
    name:           str       = Field(..., max_length=200)
    location:       str       = Field(..., description="Location or 'All'")
    employeeGroups: List[str] = ["all"]
    isDefault:      bool      = False


class HolidayCalendarUpdateIn(BaseModel):
    name:           Optional[str]      = None
    location:       Optional[str]      = None
    employeeGroups: Optional[List[str]]= None
    isDefault:      Optional[bool]     = None
    isActive:       Optional[bool]     = None


class HolidayCalendarOut(BaseModel):
    id:             int
    name:           str
    location:       str
    employeeGroups: List[str]
    isDefault:      bool
    isActive:       bool
    # Display: "All Groups" when employeeGroups = ["all"]
    groupsDisplay:  str = ""
    # Status badge: "Active" | "Inactive"
    statusDisplay:  str = ""
    created_at:     datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# TAB 4 — HOLIDAY SWAP
# ══════════════════════════════════════════════════════════

class SwapRequestIn(BaseModel):
    """
    New Swap Request modal.
    Fields: Employee* · Holiday Date* (work on this day) · Work Date* (take off) · Reason*
    """
    employeeId:  str
    holidayDate: date    # date they want to work
    workDate:    date    # date they want to take off
    reason:      str     = Field(..., min_length=1)

    @model_validator(mode="after")
    def check_dates(self):
        if self.holidayDate == self.workDate:
            raise ValueError("holidayDate and workDate must be different.")
        return self


class SwapDecisionIn(BaseModel):
    approved: bool


class SwapRequestOut(BaseModel):
    id:              int
    employee_id:     str
    employeeName:    str = ""
    holidayDate:     date
    workDate:        date
    reason:          str
    status:          SwapStatusEnum
    approvalWorkflow:List[dict]
    approvedAt:      Optional[datetime]
    approvedBy:      Optional[str]
    rejectedAt:      Optional[datetime]
    rejectedBy:      Optional[str]
    submittedAt:     datetime

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# TAB 5 — CARRY FORWARD
# ══════════════════════════════════════════════════════════

class CarryForwardIn(BaseModel):
    """
    Process Carry Forward modal.
    Fields: Employee* · From Year · To Year · Select Unused Optional Holidays (checkboxes)
    Only optional holidays with allowCarryForward=True appear in the list.
    """
    employeeId: str
    fromYear:   int = Field(..., ge=2000, le=2100)
    toYear:     int = Field(..., ge=2000, le=2100)
    holidays:   List[int] = Field(..., min_length=1,
                                   description="List of holiday IDs to carry forward")

    @model_validator(mode="after")
    def check_years(self):
        if self.toYear <= self.fromYear:
            raise ValueError("toYear must be > fromYear")
        return self


class CarryForwardOut(BaseModel):
    id:              int
    employee_id:     str
    employeeName:    str = ""
    fromYear:        int
    toYear:          int
    holidays:        List[int]
    holidayCount:    int
    status:          CarryForwardStatusEnum
    processedAt:     datetime
    processedByName: str

    model_config = {"from_attributes": True}


# ══════════════════════════════════════════════════════════
# CALENDAR VIEW  (month grid)
# ══════════════════════════════════════════════════════════

class CalendarDayOut(BaseModel):
    day:           int
    date:          date
    isToday:       bool
    holiday:       Optional[HolidayOut] = None
    isHoliday:     bool = False


class CalendarMonthOut(BaseModel):
    year:          int
    month:         int
    monthName:     str
    weeks:         List[List[CalendarDayOut]]  # 6 rows × 7 cols (Sun-Sat)


# ══════════════════════════════════════════════════════════
# FILTER OPTIONS  (dropdowns)
# ══════════════════════════════════════════════════════════

class FilterOptionsOut(BaseModel):
    categories: List[str]
    locations:  List[str]
    statuses:   List[str]


# ══════════════════════════════════════════════════════════
# GENERIC
# ══════════════════════════════════════════════════════════

class MessageResponse(BaseModel):
    message: str
