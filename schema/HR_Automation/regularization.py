"""
schemas/regularization.py
Pydantic v2 schemas for Regularization Workflow module — all 4 tabs.
Field names match the component's requestForm state exactly.
"""

from __future__ import annotations
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
from pydantic import BaseModel, Field, model_validator

from model.HR_Automation.regularization import (
    RequestTypeEnum, RequestStatusEnum,
    DutyTypeEnum, IssueTypeEnum,
)
from model.HR_Automation.attendance_capture import PunchTypeEnum
from model.HR_Automation.attendance_reports import ReportFormatEnum
# ─────────────────────────────────────────────────────────
# APPROVAL WORKFLOW STEP
# ─────────────────────────────────────────────────────────

class WorkflowStep(BaseModel):
    level:    int
    approver: str
    status:   str    = "pending"    # pending | approved | rejected
    required: bool   = True
    remarks:  str    = ""


# ─────────────────────────────────────────────────────────
# TAB 1 — REQUEST CREATE / UPDATE
# ─────────────────────────────────────────────────────────

class RegularizationRequestIn(BaseModel):
    """
    New Request modal payload.
    Required: employeeId · requestType · reason · remarks
    Type-specific fields filled based on requestType:
      missing   → dateTime
      incorrect → originalTime + correctedTime
      forgot    → date + punchType + approxTime
      wfh       → date + location + summary
      on_duty   → date + fromTime + toTime + dutyType + purpose
    """
    employeeId:    str
    requestType:   RequestTypeEnum

    # missing punch
    dateTime:      Optional[datetime] = None

    # incorrect time
    originalTime:  Optional[datetime] = None
    correctedTime: Optional[datetime] = None

    # forgot punch
    date:          Optional[date]     = None
    punchType:     Optional[PunchTypeEnum] = None
    approxTime:    Optional[str]      = None    # "HH:MM"

    # wfh
    location:      Optional[str]      = None
    summary:       Optional[str]      = None

    # on-duty
    fromTime:      Optional[str]      = None    # "HH:MM"
    toTime:        Optional[str]      = None
    dutyType:      Optional[DutyTypeEnum] = None
    purpose:       Optional[str]      = None

    # common
    reason:        str                = Field(..., min_length=1)
    remarks:       str                = Field(..., min_length=1)

    @model_validator(mode="after")
    def validate_type_fields(self):
        t = self.requestType
        if t == RequestTypeEnum.missing and not self.dateTime:
            raise ValueError("dateTime is required for Missing Punch.")
        if t == RequestTypeEnum.incorrect and (not self.originalTime or not self.correctedTime):
            raise ValueError("originalTime and correctedTime are required for Incorrect Time.")
        if t == RequestTypeEnum.forgot and not self.date:
            raise ValueError("date is required for Forgot Punch.")
        if t == RequestTypeEnum.wfh and (not self.date or not self.location):
            raise ValueError("date and location are required for WFH.")
        if t == RequestTypeEnum.on_duty and (not self.date or not self.fromTime or not self.toTime):
            raise ValueError("date, fromTime, toTime are required for On-Duty.")
        return self


# ─────────────────────────────────────────────────────────
# REQUEST RESPONSE
# ─────────────────────────────────────────────────────────

class RegularizationRequestOut(BaseModel):
    id:               int
    employee_id:      str
    employeeName:     str  = ""
    department:       str  = ""
    requestType:      RequestTypeEnum
    status:           RequestStatusEnum

    # Type-specific
    dateTime:         Optional[datetime]
    originalTime:     Optional[datetime]
    correctedTime:    Optional[datetime]
    date:             Optional[date]
    punchType:        Optional[PunchTypeEnum]
    approxTime:       Optional[str]
    location:         Optional[str]
    workSummary:      Optional[str]
    fromTime:         Optional[str]
    toTime:           Optional[str]
    dutyType:         Optional[DutyTypeEnum]
    purpose:          Optional[str]

    # Common
    reason:           str
    remarks:          str
    attachments:      List[str]  = []
    approvalWorkflow: List[dict] = []

    # Decision
    approvedAt:       Optional[datetime]
    rejectedAt:       Optional[datetime]
    rejectionReason:  Optional[str]
    isAutoRejected:   bool = False

    # Audit
    submittedAt:      datetime
    submittedBy:      str

    # Display helper
    displayDateTime:  str  = ""   # formatted date/time for Date/Time column

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# APPROVE / REJECT
# ─────────────────────────────────────────────────────────

class ApproveRejectIn(BaseModel):
    """
    Approval modal payload.
    action: approve | reject | request_changes
    """
    action:  str   = Field(..., description="approve | reject | request_changes")
    remarks: str   = ""


# ─────────────────────────────────────────────────────────
# LIST RESPONSE
# ─────────────────────────────────────────────────────────

class RegularizationListOut(BaseModel):
    total:      int
    page:       int
    page_size:  int
    items:      List[RegularizationRequestOut]


# ─────────────────────────────────────────────────────────
# TAB 2 — AUTO-REJECT RULES
# ─────────────────────────────────────────────────────────

class AutoRejectRuleOut(BaseModel):
    id:          int
    requestType: RequestTypeEnum
    days:        int
    enabled:     bool
    updated_at:  datetime

    # Display string (shown in table)
    requestTypeLabel: str = ""   # "Missing Punch" | "Forgot Punch"
    daysDisplay:      str = ""   # "7 days"
    statusDisplay:    str = ""   # "Enabled" | "Disabled"

    model_config = {"from_attributes": True}


class AutoRejectRuleUpdateIn(BaseModel):
    days:    Optional[int]  = None
    enabled: Optional[bool] = None


# ─────────────────────────────────────────────────────────
# STATISTICS  (Settings tab right panel)
# ─────────────────────────────────────────────────────────

class RequestStatisticsOut(BaseModel):
    totalRequests: int
    pending:       int
    approved:      int
    rejected:      int


# ─────────────────────────────────────────────────────────
# TAB 3 — BULK PROCESSING
# ─────────────────────────────────────────────────────────

class BulkProcessIn(BaseModel):
    """
    Process Bulk modal payload.
    fromDate · toDate · issueType · optional employee list (CSV file handled separately)
    """
    fromDate:   date
    toDate:     date
    issueType:  IssueTypeEnum
    employeeIds: List[str] = []   # empty = all employees

    @model_validator(mode="after")
    def check_dates(self):
        if self.toDate < self.fromDate:
            raise ValueError("toDate must be >= fromDate")
        return self


class BulkProcessOut(BaseModel):
    id:             int
    fromDate:       date
    toDate:         date
    issueType:      IssueTypeEnum
    processedCount: int
    status:         str
    processedAt:    datetime
    processedByName:str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# TAB 4 — REPORTS
# ─────────────────────────────────────────────────────────

class GenerateReportIn(BaseModel):
    """
    Reports tab form:
    From Date · To Date · Request Type (All/specific) · Format (PDF/Excel/CSV)
    """
    fromDate:    date
    toDate:      date
    requestType: Optional[RequestTypeEnum] = None   # None = All Types
    format:      ReportFormatEnum           = ReportFormatEnum.pdf

    @model_validator(mode="after")
    def check_dates(self):
        if self.toDate < self.fromDate:
            raise ValueError("toDate must be >= fromDate")
        return self


class ReportSummary(BaseModel):
    totalRequests: int
    pending:       int
    approved:      int
    rejected:      int
    byType:        dict = {}
    byDepartment:  dict = {}


class RegularizationReportOut(BaseModel):
    id:              int
    fromDate:        date
    toDate:          date
    requestType:     Optional[RequestTypeEnum]
    format:          ReportFormatEnum
    fileName:        str
    totalRecords:    int
    summary:         dict
    generatedAt:     datetime
    generatedByName: str

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────
# GENERIC
# ─────────────────────────────────────────────────────────

class MessageResponse(BaseModel):
    message: str
