"""
Final Settlement Schemas
========================
Pydantic v2 — ConfigDict(from_attributes=True) on every Response model.
All monetary fields use Decimal for precision.
"""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ──────────────────────────────────────────────────────────────────────────────
# Notice Period
# ──────────────────────────────────────────────────────────────────────────────

class NoticePeriodCreate(BaseModel):
    verified: bool = False
    days_served: int = 0
    required_days: int = 90
    verification_date: Optional[date] = None
    verified_by_name: Optional[str] = None
    waiver_approved: bool = False
    waiver_remarks: Optional[str] = None


class NoticePeriodUpdate(BaseModel):
    verified: Optional[bool] = None
    days_served: Optional[int] = None
    required_days: Optional[int] = None
    verification_date: Optional[date] = None
    verified_by_name: Optional[str] = None
    waiver_approved: Optional[bool] = None
    waiver_remarks: Optional[str] = None


class NoticePeriodResponse(BaseModel):
    id: int
    settlement_id: int
    verified: bool
    days_served: int
    required_days: int
    shortfall_days: int
    recovery_amount: Decimal
    verification_date: Optional[date]
    verified_by_name: Optional[str]
    waiver_approved: bool
    waiver_remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Salary Breakdown
# ──────────────────────────────────────────────────────────────────────────────

class SalaryBreakdownCreate(BaseModel):
    basic: Decimal = Decimal("0")
    hra: Decimal = Decimal("0")
    special_allowance: Decimal = Decimal("0")
    other_allowances: Decimal = Decimal("0")
    days_worked: int = 0
    working_days_in_month: int = 30
    arrears: Decimal = Decimal("0")
    last_working_day: Optional[date] = None
    payment_due_date: Optional[date] = None


class SalaryBreakdownUpdate(BaseModel):
    basic: Optional[Decimal] = None
    hra: Optional[Decimal] = None
    special_allowance: Optional[Decimal] = None
    other_allowances: Optional[Decimal] = None
    days_worked: Optional[int] = None
    working_days_in_month: Optional[int] = None
    arrears: Optional[Decimal] = None
    last_working_day: Optional[date] = None
    payment_due_date: Optional[date] = None


class SalaryBreakdownResponse(BaseModel):
    id: int
    settlement_id: int
    basic: Decimal
    hra: Decimal
    special_allowance: Decimal
    other_allowances: Decimal
    days_worked: int
    working_days_in_month: int
    daily_rate: Decimal
    salary_for_days: Decimal
    arrears: Decimal
    last_working_day: Optional[date]
    payment_due_date: Optional[date]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Leave Encashment
# ──────────────────────────────────────────────────────────────────────────────

class LeaveEncashmentCreate(BaseModel):
    earned_leave_balance: Decimal = Decimal("0")
    casual_leave_balance: Decimal = Decimal("0")
    sick_leave_balance: Decimal = Decimal("0")
    encashment_rate: Decimal = Decimal("0")
    encashment_policy: str = "Earned leave only"


class LeaveEncashmentUpdate(BaseModel):
    earned_leave_balance: Optional[Decimal] = None
    casual_leave_balance: Optional[Decimal] = None
    sick_leave_balance: Optional[Decimal] = None
    encashment_rate: Optional[Decimal] = None
    encashment_policy: Optional[str] = None


class LeaveEncashmentResponse(BaseModel):
    id: int
    settlement_id: int
    earned_leave_balance: Decimal
    casual_leave_balance: Decimal
    sick_leave_balance: Decimal
    encashment_rate: Decimal
    encashable_days: Decimal
    total_encashment: Decimal
    encashment_policy: str

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Bonus
# ──────────────────────────────────────────────────────────────────────────────

class BonusCreate(BaseModel):
    annual_bonus: Decimal = Decimal("0")
    pro_rata_days: int = 0
    is_eligible: bool = True
    calculation_method: str = "Pro-rata based on days worked"
    remarks: Optional[str] = None


class BonusUpdate(BaseModel):
    annual_bonus: Optional[Decimal] = None
    pro_rata_days: Optional[int] = None
    is_eligible: Optional[bool] = None
    calculation_method: Optional[str] = None
    remarks: Optional[str] = None


class BonusResponse(BaseModel):
    id: int
    settlement_id: int
    annual_bonus: Decimal
    pro_rata_days: int
    pro_rata_bonus: Decimal
    is_eligible: bool
    calculation_method: str
    remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Gratuity
# ──────────────────────────────────────────────────────────────────────────────

class GratuityCreate(BaseModel):
    completed_years: Decimal = Decimal("0")
    last_drawn_basic: Decimal = Decimal("0")
    eligibility_years: int = 5
    remarks: Optional[str] = None


class GratuityUpdate(BaseModel):
    completed_years: Optional[Decimal] = None
    last_drawn_basic: Optional[Decimal] = None
    eligibility_years: Optional[int] = None
    remarks: Optional[str] = None


class GratuityResponse(BaseModel):
    id: int
    settlement_id: int
    completed_years: Decimal
    last_drawn_basic: Decimal
    gratuity_amount: Decimal
    is_eligible: bool
    eligibility_years: int
    remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Deductions
# ──────────────────────────────────────────────────────────────────────────────

class DeductionCreate(BaseModel):
    loan_outstanding: Decimal = Decimal("0")
    advance_amount: Decimal = Decimal("0")
    id_card_deduction: Decimal = Decimal("0")
    uniform_deduction: Decimal = Decimal("0")
    other_deductions: Decimal = Decimal("0")
    tds_deduction: Decimal = Decimal("0")
    penalty_amount: Decimal = Decimal("0")
    deduction_remarks: Optional[str] = None


class DeductionUpdate(BaseModel):
    loan_outstanding: Optional[Decimal] = None
    advance_amount: Optional[Decimal] = None
    id_card_deduction: Optional[Decimal] = None
    uniform_deduction: Optional[Decimal] = None
    other_deductions: Optional[Decimal] = None
    tds_deduction: Optional[Decimal] = None
    penalty_amount: Optional[Decimal] = None
    deduction_remarks: Optional[str] = None


class DeductionResponse(BaseModel):
    id: int
    settlement_id: int
    loan_outstanding: Decimal
    advance_amount: Decimal
    notice_period_recovery: Decimal
    asset_penalty: Decimal
    id_card_deduction: Decimal
    uniform_deduction: Decimal
    other_deductions: Decimal
    tds_deduction: Decimal
    penalty_amount: Decimal
    total_deductions: Decimal
    deduction_remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Asset
# ──────────────────────────────────────────────────────────────────────────────

class AssetCreate(BaseModel):
    asset_id: str
    asset_name: str
    asset_tag: Optional[str] = None
    category: Optional[str] = None
    return_status: str = "pending"
    return_date: Optional[date] = None
    condition: Optional[str] = None
    penalty: Decimal = Decimal("0")
    remarks: Optional[str] = None


class AssetUpdate(BaseModel):
    return_status: Optional[str] = None
    return_date: Optional[date] = None
    condition: Optional[str] = None
    penalty: Optional[Decimal] = None
    remarks: Optional[str] = None


class AssetResponse(BaseModel):
    id: int
    settlement_id: int
    asset_id: str
    asset_name: str
    asset_tag: Optional[str]
    category: Optional[str]
    return_status: str
    return_date: Optional[date]
    condition: Optional[str]
    penalty: Decimal
    remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Payment
# ──────────────────────────────────────────────────────────────────────────────

class PaymentCreate(BaseModel):
    payment_method: str = "Bank Transfer"
    payment_mode: str = "NEFT"
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    payment_date: Optional[date] = None
    remarks: Optional[str] = None


class PaymentUpdate(BaseModel):
    payment_method: Optional[str] = None
    payment_mode: Optional[str] = None
    account_number: Optional[str] = None
    ifsc_code: Optional[str] = None
    bank_name: Optional[str] = None
    payment_date: Optional[date] = None
    status: Optional[str] = None
    reference_number: Optional[str] = None
    utr_number: Optional[str] = None
    processed_by_name: Optional[str] = None
    payment_proof_url: Optional[str] = None
    remarks: Optional[str] = None


class PaymentResponse(BaseModel):
    id: int
    settlement_id: int
    payment_method: str
    payment_mode: str
    account_number: Optional[str]
    ifsc_code: Optional[str]
    bank_name: Optional[str]
    payment_date: Optional[date]
    status: str
    reference_number: Optional[str]
    utr_number: Optional[str]
    processed_by_name: Optional[str]
    processed_date: Optional[datetime]
    payment_proof_url: Optional[str]
    remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Document
# ──────────────────────────────────────────────────────────────────────────────

class DocumentCreate(BaseModel):
    document_type: str   # Form16, Form19, Form10C, Experience Letter, Relieving Letter
    financial_year: Optional[str] = None
    pf_account_no: Optional[str] = None


class DocumentUpdate(BaseModel):
    generated: Optional[bool] = None
    generated_date: Optional[datetime] = None
    issued: Optional[bool] = None
    issued_date: Optional[datetime] = None
    download_url: Optional[str] = None
    generated_by: Optional[str] = None


class DocumentResponse(BaseModel):
    id: int
    settlement_id: int
    document_type: str
    generated: bool
    generated_date: Optional[datetime]
    issued: bool
    issued_date: Optional[datetime]
    financial_year: Optional[str]
    pf_account_no: Optional[str]
    download_url: Optional[str]
    generated_by: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Timeline
# ──────────────────────────────────────────────────────────────────────────────

class TimelineResponse(BaseModel):
    id: int
    settlement_id: int
    event: str
    event_date: Optional[date]
    is_completed: bool
    notes: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Approval Log
# ──────────────────────────────────────────────────────────────────────────────

class ApprovalLogResponse(BaseModel):
    id: int
    settlement_id: int
    action: str
    actioned_by: Optional[int]
    actioned_by_name: Optional[str]
    actioned_at: datetime
    from_status: Optional[str]
    to_status: Optional[str]
    remarks: Optional[str]

    model_config = ConfigDict(from_attributes=True)


# ──────────────────────────────────────────────────────────────────────────────
# Settlement Header — Create / Update
# ──────────────────────────────────────────────────────────────────────────────

class FinalSettlementCreate(BaseModel):
    employee_id: int
    employee_code: str
    employee_name: str
    department: Optional[str] = None
    designation: Optional[str] = None
    date_of_joining: Optional[date] = None
    uan_number: Optional[str] = None
    pf_number: Optional[str] = None
    pan_number: Optional[str] = None
    exit_type: str = "Resignation"
    resignation_date: Optional[date] = None
    last_working_date: date
    notice_period_required_days: int = 90
    initiated_by_name: Optional[str] = None
    initiated_date: Optional[date] = None
    remarks: Optional[str] = None

    # Optional nested sub-blocks at creation time
    notice_period: Optional[NoticePeriodCreate] = None
    salary_breakdown: Optional[SalaryBreakdownCreate] = None
    leave_encashment: Optional[LeaveEncashmentCreate] = None
    bonus: Optional[BonusCreate] = None
    gratuity: Optional[GratuityCreate] = None
    deduction: Optional[DeductionCreate] = None
    assets: Optional[List[AssetCreate]] = None
    payment: Optional[PaymentCreate] = None


class FinalSettlementUpdate(BaseModel):
    exit_type: Optional[str] = None
    resignation_date: Optional[date] = None
    last_working_date: Optional[date] = None
    notice_period_required_days: Optional[int] = None
    remarks: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Approval / Status actions
# ──────────────────────────────────────────────────────────────────────────────

class ApprovalPayload(BaseModel):
    approved_by: Optional[int] = None
    approved_by_name: Optional[str] = None
    remarks: Optional[str] = None


class RejectionPayload(BaseModel):
    rejected_by: Optional[int] = None
    rejected_by_name: Optional[str] = None
    rejection_reason: str


class PaymentProcessPayload(BaseModel):
    reference_number: Optional[str] = None
    utr_number: Optional[str] = None
    payment_date: Optional[date] = None
    processed_by_name: Optional[str] = None
    payment_proof_url: Optional[str] = None
    remarks: Optional[str] = None


# ──────────────────────────────────────────────────────────────────────────────
# Full Settlement Response (nested)
# ──────────────────────────────────────────────────────────────────────────────

class FinalSettlementResponse(BaseModel):
    id: int
    settlement_code: str
    employee_id: int
    employee_code: str
    employee_name: str
    department: Optional[str]
    designation: Optional[str]
    date_of_joining: Optional[date]
    uan_number: Optional[str]
    pf_number: Optional[str]
    pan_number: Optional[str]
    exit_type: str
    resignation_date: Optional[date]
    last_working_date: date
    notice_period_required_days: int
    total_additions: Decimal
    total_deductions: Decimal
    net_settlement: Decimal
    status: str
    initiated_by: Optional[int]
    initiated_by_name: Optional[str]
    initiated_date: Optional[date]
    approved_by: Optional[int]
    approved_by_name: Optional[str]
    approved_date: Optional[date]
    rejection_reason: Optional[str]
    remarks: Optional[str]
    last_calculated_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    # Nested
    notice_period: Optional[NoticePeriodResponse] = None
    salary_breakdown: Optional[SalaryBreakdownResponse] = None
    leave_encashment: Optional[LeaveEncashmentResponse] = None
    bonus: Optional[BonusResponse] = None
    gratuity: Optional[GratuityResponse] = None
    deduction: Optional[DeductionResponse] = None
    assets: Optional[List[AssetResponse]] = None
    payment: Optional[PaymentResponse] = None
    documents: Optional[List[DocumentResponse]] = None
    timeline: Optional[List[TimelineResponse]] = None
    approval_logs: Optional[List[ApprovalLogResponse]] = None

    model_config = ConfigDict(from_attributes=True)


class FinalSettlementListItem(BaseModel):
    """Lightweight row for list/search endpoints — no nested blocks."""
    id: int
    settlement_code: str
    employee_id: int
    employee_code: str
    employee_name: str
    department: Optional[str]
    designation: Optional[str]
    exit_type: str
    last_working_date: date
    net_settlement: Decimal
    total_additions: Decimal
    total_deductions: Decimal
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PaginatedSettlementList(BaseModel):
    total: int
    page: int
    page_size: int
    items: List[FinalSettlementListItem]


# ──────────────────────────────────────────────────────────────────────────────
# Stats / Dashboard
# ──────────────────────────────────────────────────────────────────────────────

class SettlementStatsResponse(BaseModel):
    current_settlement: Decimal       # Net settlement amount (current selected)
    total_additions: Decimal
    total_deductions: Decimal
    approval_status: str
    total_pending_count: int
    total_approved_count: int
    total_paid_count: int
    total_cancelled_count: int
