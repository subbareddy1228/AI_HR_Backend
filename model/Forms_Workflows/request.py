"""
model/Forms_Workflows/request.py
=================================
Request Management data models — covers every request category visible in the
Request Management UI:
  • Personal Information  (Bank Account Change, Address Change, Emergency Contact,
                           Phone Number, Family Details, Nominee Change)
  • Work-Related          (WFH, Remote Work Approval, Shift Change, Dept Transfer,
                           Reporting Manager Change, Desk/Seat Change)
  • Administrative        (ID Card Reissue, Access Card, Parking Slot, Locker,
                           Stationery, Business Card)
  • Financial             (Salary Advance, Reimbursement Claim, Loan Application,
                           Investment Declaration 80C, Tax Regime Change,
                           Salary Certificate)
  • Travel & Expense      (Business Travel, Expense Reimbursement, Travel Advance,
                           Mileage Claim, Per Diem Claim)
  • IT & Systems          (Software Access, VPN Access, Email Distribution List,
                           System/Application Access, Hardware Request)
  • Feedback              (General Feedback, HR Grievance, Suggestion Box,
                           POSH Complaint, Ethics Violation Reporting)

All categories share a single `RequestManagement` master table with typed
detail tables for each category, connected by a one-to-one FK so each row
only stores what is relevant.
"""

from __future__ import annotations

from datetime import datetime
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import relationship
from core.database import Base
import enum


# ─────────────────────────────────────────────
# Enum helpers (kept as Python str-enums so they
# are importable elsewhere without SQLAlchemy)
# ─────────────────────────────────────────────

class RequestCategory(str, enum.Enum):
    PERSONAL_INFORMATION = "Personal Information"
    WORK_RELATED         = "Work-Related"
    ADMINISTRATIVE       = "Administrative"
    FINANCIAL            = "Financial"
    TRAVEL_EXPENSE       = "Travel & Expense"
    IT_SYSTEMS           = "IT & Systems"
    FEEDBACK             = "Feedback"


class RequestType(str, enum.Enum):
    # Personal Information
    BANK_ACCOUNT_CHANGE      = "Bank Account Change Request"
    ADDRESS_CHANGE           = "Address Change"
    EMERGENCY_CONTACT_UPDATE = "Emergency Contact Update"
    PHONE_NUMBER_UPDATE      = "Phone Number Update"
    FAMILY_DETAILS_UPDATE    = "Family Details Update"
    NOMINEE_CHANGE           = "Nominee Change Request"

    # Work-Related
    WORK_FROM_HOME           = "Work-from-Home Request"
    REMOTE_WORK_APPROVAL     = "Remote Work Approval"
    SHIFT_CHANGE             = "Shift Change Request"
    DEPARTMENT_TRANSFER      = "Department Transfer Request"
    REPORTING_MANAGER_CHANGE = "Reporting Manager Change Request"
    DESK_SEAT_CHANGE         = "Desk/Seat Change Request"

    # Administrative
    ID_CARD_REISSUE          = "ID Card Reissue"
    ACCESS_CARD_REQUEST      = "Access Card Request"
    PARKING_SLOT_REQUEST     = "Parking Slot Request"
    LOCKER_ASSIGNMENT        = "Locker Assignment Request"
    STATIONERY_REQUISITION   = "Stationery Requisition"
    BUSINESS_CARD_REQUEST    = "Business Card Request"

    # Financial
    SALARY_ADVANCE           = "Salary Advance"
    REIMBURSEMENT_CLAIM      = "Reimbursement Claim"
    LOAN_APPLICATION         = "Loan Application"
    INVESTMENT_DECLARATION   = "Investment Declaration (80C)"
    TAX_REGIME_CHANGE        = "Tax Regime Change Request"
    SALARY_CERTIFICATE       = "Salary Certificate Request"

    # Travel & Expense
    BUSINESS_TRAVEL          = "Business Travel Request"
    EXPENSE_REIMBURSEMENT    = "Expense Reimbursement"
    TRAVEL_ADVANCE           = "Travel Advance Request"
    MILEAGE_CLAIM            = "Mileage Claim"
    PER_DIEM_CLAIM           = "Per Diem Claim"

    # IT & Systems
    SOFTWARE_ACCESS          = "Software Access"
    VPN_ACCESS               = "VPN Access Request"
    EMAIL_DISTRIBUTION_LIST  = "Email Distribution List Request"
    SYSTEM_APP_ACCESS        = "System/Application Access"
    HARDWARE_REQUEST         = "Hardware Request"

    # Feedback
    GENERAL_FEEDBACK         = "General Feedback"
    HR_GRIEVANCE             = "HR Grievance"
    SUGGESTION_BOX           = "Suggestion Box"
    POSH_COMPLAINT           = "POSH Complaint"
    ETHICS_VIOLATION         = "Ethics Violation Reporting"


class RequestStatus(str, enum.Enum):
    OPEN        = "Open"
    IN_PROGRESS = "In Progress"
    PENDING     = "Pending"
    PROCESSING  = "Processing"
    SUBMITTED   = "Submitted"
    APPROVED    = "Approved"
    REJECTED    = "Rejected"
    COMPLETED   = "Completed"
    CANCELLED   = "Cancelled"
    CLOSED      = "Closed"


class RequestPriority(str, enum.Enum):
    LOW    = "Low"
    MEDIUM = "Medium"
    HIGH   = "High"


# ─────────────────────────────────────────────
# SLA configuration per request type
# (used by the router to stamp sla_days on create)
# ─────────────────────────────────────────────

SLA_DAYS: dict[str, str] = {
    # Personal Information
    RequestType.BANK_ACCOUNT_CHANGE:      "2-3 business days",
    RequestType.ADDRESS_CHANGE:           "1-2 business days",
    RequestType.EMERGENCY_CONTACT_UPDATE: "1 business day",
    RequestType.PHONE_NUMBER_UPDATE:      "1 business day",
    RequestType.FAMILY_DETAILS_UPDATE:    "2-3 business days",
    RequestType.NOMINEE_CHANGE:           "3-5 business days",
    # Work-Related
    RequestType.WORK_FROM_HOME:           "2-3 business days",
    RequestType.REMOTE_WORK_APPROVAL:     "5-7 business days",
    RequestType.SHIFT_CHANGE:             "3-5 business days",
    RequestType.DEPARTMENT_TRANSFER:      "7-10 business days",
    RequestType.REPORTING_MANAGER_CHANGE: "5-7 business days",
    RequestType.DESK_SEAT_CHANGE:         "2-3 business days",
    # Administrative
    RequestType.ID_CARD_REISSUE:          "3-5 business days",
    RequestType.ACCESS_CARD_REQUEST:      "2-3 business days",
    RequestType.PARKING_SLOT_REQUEST:     "3-5 business days",
    RequestType.LOCKER_ASSIGNMENT:        "2-3 business days",
    RequestType.STATIONERY_REQUISITION:   "1-2 business days",
    RequestType.BUSINESS_CARD_REQUEST:    "5-7 business days",
    # Financial
    RequestType.SALARY_ADVANCE:           "3-5 business days",
    RequestType.REIMBURSEMENT_CLAIM:      "5-7 business days",
    RequestType.LOAN_APPLICATION:         "7-10 business days",
    RequestType.INVESTMENT_DECLARATION:   "5-7 business days",
    RequestType.TAX_REGIME_CHANGE:        "3-5 business days",
    RequestType.SALARY_CERTIFICATE:       "2-3 business days",
    # Travel & Expense
    RequestType.BUSINESS_TRAVEL:          "3-5 business days",
    RequestType.EXPENSE_REIMBURSEMENT:    "5-7 business days",
    RequestType.TRAVEL_ADVANCE:           "3-5 business days",
    RequestType.MILEAGE_CLAIM:            "3-5 business days",
    RequestType.PER_DIEM_CLAIM:           "3-5 business days",
    # IT & Systems
    RequestType.SOFTWARE_ACCESS:          "1-2 business days",
    RequestType.VPN_ACCESS:              "2-3 business days",
    RequestType.EMAIL_DISTRIBUTION_LIST:  "1-2 business days",
    RequestType.SYSTEM_APP_ACCESS:        "2-3 business days",
    RequestType.HARDWARE_REQUEST:         "5-7 business days",
    # Feedback
    RequestType.GENERAL_FEEDBACK:         "Acknowledgement in 1 day",
    RequestType.HR_GRIEVANCE:             "Initial response in 2 business days",
    RequestType.SUGGESTION_BOX:           "Review within 5 business days",
    RequestType.POSH_COMPLAINT:           "Immediate response within 24 hours",
    RequestType.ETHICS_VIOLATION:         "Immediate investigation initiation",
}

PRIORITY_MAP: dict[str, str] = {
    RequestType.BANK_ACCOUNT_CHANGE:      RequestPriority.HIGH,
    RequestType.SALARY_ADVANCE:           RequestPriority.HIGH,
    RequestType.LOAN_APPLICATION:         RequestPriority.HIGH,
    RequestType.POSH_COMPLAINT:           RequestPriority.HIGH,
    RequestType.ETHICS_VIOLATION:         RequestPriority.HIGH,
    RequestType.REMOTE_WORK_APPROVAL:     RequestPriority.HIGH,
    RequestType.DEPARTMENT_TRANSFER:      RequestPriority.HIGH,
    RequestType.REPORTING_MANAGER_CHANGE: RequestPriority.HIGH,
    RequestType.BUSINESS_TRAVEL:          RequestPriority.HIGH,
    RequestType.TRAVEL_ADVANCE:           RequestPriority.HIGH,
    RequestType.SHIFT_CHANGE:             RequestPriority.MEDIUM,
    RequestType.WORK_FROM_HOME:           RequestPriority.MEDIUM,
    RequestType.ID_CARD_REISSUE:          RequestPriority.MEDIUM,
    RequestType.ACCESS_CARD_REQUEST:      RequestPriority.MEDIUM,
    RequestType.PARKING_SLOT_REQUEST:     RequestPriority.MEDIUM,
    RequestType.REIMBURSEMENT_CLAIM:      RequestPriority.MEDIUM,
    RequestType.INVESTMENT_DECLARATION:   RequestPriority.MEDIUM,
    RequestType.TAX_REGIME_CHANGE:        RequestPriority.MEDIUM,
    RequestType.EXPENSE_REIMBURSEMENT:    RequestPriority.MEDIUM,
    RequestType.MILEAGE_CLAIM:            RequestPriority.MEDIUM,
    RequestType.PER_DIEM_CLAIM:           RequestPriority.MEDIUM,
    RequestType.VPN_ACCESS:               RequestPriority.MEDIUM,
    RequestType.SYSTEM_APP_ACCESS:        RequestPriority.MEDIUM,
    RequestType.HARDWARE_REQUEST:         RequestPriority.MEDIUM,
    RequestType.HR_GRIEVANCE:             RequestPriority.MEDIUM,
    RequestType.NOMINEE_CHANGE:           RequestPriority.MEDIUM,
    RequestType.FAMILY_DETAILS_UPDATE:    RequestPriority.MEDIUM,
}  # All others default to LOW


def default_priority(request_type: str) -> str:
    return PRIORITY_MAP.get(request_type, RequestPriority.LOW)


# ─────────────────────────────────────────────────────────────────────────────
# MASTER REQUEST TABLE
# ─────────────────────────────────────────────────────────────────────────────

class RequestManagement(Base):
    """
    Central request table.  Every request type shares this master record.
    Category-specific fields live in their own detail table referenced by
    `request_id` FK.
    """
    __tablename__ = "request_management"

    id              = Column(BigInteger, primary_key=True, index=True, autoincrement=True)

    # Auto-generated public identifier: REQ-YYYY-NNNNNN
    request_id      = Column(String(20), unique=True, nullable=False, index=True)

    # Taxonomy
    category        = Column(String(50),  nullable=False, index=True)   # RequestCategory
    request_type    = Column(String(100), nullable=False, index=True)   # RequestType

    # Employee who raised the request
    employee_id     = Column(Integer, ForeignKey("employees.id"), nullable=True, index=True)
    employee_name   = Column(String(255), nullable=True)
    employee_email  = Column(String(255), nullable=True)
    department      = Column(String(100), nullable=True)
    location        = Column(String(100), nullable=True)

    # Core fields
    subject         = Column(String(500), nullable=False)
    description     = Column(Text,        nullable=True)

    # Workflow linkage
    workflow        = Column(String(100), nullable=True)   # workflow name / type
    workflow_instance_id = Column(
        Integer, ForeignKey("workflow_instances.id"), nullable=True, index=True
    )

    # Status & priority
    status          = Column(String(50), nullable=False, default=RequestStatus.OPEN, index=True)
    priority        = Column(String(20), nullable=False, default=RequestPriority.MEDIUM)
    sla_days        = Column(String(50), nullable=True)

    # Assignment
    assigned_to     = Column(String(100), nullable=True)
    assigned_at     = Column(DateTime,    nullable=True)

    # Resolution
    resolution_note = Column(Text,     nullable=True)
    resolved_at     = Column(DateTime, nullable=True)
    resolved_by     = Column(String(100), nullable=True)

    # Auto-generated description flag (from "Auto-description" badge in UI)
    auto_description_generated = Column(Boolean, default=False, nullable=False)

    # Soft delete / audit
    is_deleted      = Column(Boolean, default=False, nullable=False)
    deleted_at      = Column(DateTime, nullable=True)
    submitted_at    = Column(DateTime, default=datetime.utcnow, nullable=False)
    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow, nullable=False)

    # ── Relationships ──────────────────────────────────────────────────────
    workflow_instance = relationship("WorkflowInstance", foreign_keys=[workflow_instance_id])

    # Detail tables (uselist=False = one-to-one)
    personal_info_detail  = relationship("RequestPersonalInfoDetail",  back_populates="request", uselist=False, cascade="all, delete-orphan")
    work_related_detail   = relationship("RequestWorkRelatedDetail",   back_populates="request", uselist=False, cascade="all, delete-orphan")
    admin_detail          = relationship("RequestAdminDetail",         back_populates="request", uselist=False, cascade="all, delete-orphan")
    financial_detail      = relationship("RequestFinancialDetail",     back_populates="request", uselist=False, cascade="all, delete-orphan")
    travel_expense_detail = relationship("RequestTravelExpenseDetail", back_populates="request", uselist=False, cascade="all, delete-orphan")
    it_systems_detail     = relationship("RequestITSystemsDetail",     back_populates="request", uselist=False, cascade="all, delete-orphan")
    feedback_detail       = relationship("RequestFeedbackDetail",      back_populates="request", uselist=False, cascade="all, delete-orphan")

    comments    = relationship("RequestComment",    back_populates="request", cascade="all, delete-orphan", order_by="RequestComment.created_at")
    attachments = relationship("RequestAttachment", back_populates="request", cascade="all, delete-orphan")
    status_logs = relationship("RequestStatusLog",  back_populates="request", cascade="all, delete-orphan", order_by="RequestStatusLog.changed_at")

    __table_args__ = (
        Index("ix_rm_category_status",  "category", "status"),
        Index("ix_rm_employee_status",  "employee_id", "status"),
        Index("ix_rm_location_status",  "location", "status"),
        Index("ix_rm_submitted_at",     "submitted_at"),
    )


# ─────────────────────────────────────────────────────────────────────────────
# CATEGORY DETAIL TABLES
# ─────────────────────────────────────────────────────────────────────────────

class RequestPersonalInfoDetail(Base):
    """
    Stores additional fields for Personal Information category requests.
    Covers: Bank Account Change, Address Change, Emergency Contact Update,
            Phone Number Update, Family Details Update, Nominee Change.
    """
    __tablename__ = "request_personal_info_detail"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)

    # ── Bank Account Change ───────────────────────────────────
    bank_name           = Column(String(255), nullable=True)
    account_number      = Column(String(50),  nullable=True)   # store masked
    account_holder_name = Column(String(255), nullable=True)
    ifsc_code           = Column(String(20),  nullable=True)
    account_type        = Column(String(50),  nullable=True)   # Savings / Current
    branch_name         = Column(String(255), nullable=True)

    # ── Address Change ────────────────────────────────────────
    address_type        = Column(String(20),  nullable=True)   # Current / Permanent / Both
    new_address_line1   = Column(String(500), nullable=True)
    new_address_line2   = Column(String(500), nullable=True)
    new_city            = Column(String(100), nullable=True)
    new_state           = Column(String(100), nullable=True)
    new_country         = Column(String(100), nullable=True)
    new_pincode         = Column(String(20),  nullable=True)

    # ── Emergency Contact Update ──────────────────────────────
    contact_name        = Column(String(255), nullable=True)
    contact_relationship= Column(String(100), nullable=True)
    contact_phone       = Column(String(30),  nullable=True)
    contact_email       = Column(String(255), nullable=True)

    # ── Phone Number Update ───────────────────────────────────
    phone_type          = Column(String(20),  nullable=True)   # Personal / Work
    new_phone_number    = Column(String(30),  nullable=True)

    # ── Family Details Update ─────────────────────────────────
    family_member_name  = Column(String(255), nullable=True)
    relationship_type   = Column(String(100), nullable=True)
    date_of_birth       = Column(String(20),  nullable=True)   # stored as string for flexibility
    family_details_note = Column(Text,        nullable=True)

    # ── Nominee Change ────────────────────────────────────────
    nominee_name        = Column(String(255), nullable=True)
    nominee_dob         = Column(String(20),  nullable=True)
    nominee_relationship= Column(String(100), nullable=True)
    nominee_percentage  = Column(Numeric(5, 2), nullable=True)  # allocation %

    # Common
    supporting_document_url = Column(Text, nullable=True)
    remarks                 = Column(Text, nullable=True)

    request = relationship("RequestManagement", back_populates="personal_info_detail")


class RequestWorkRelatedDetail(Base):
    """
    Work-Related category: WFH, Remote Work, Shift Change, Dept Transfer,
    Reporting Manager Change, Desk/Seat Change.
    """
    __tablename__ = "request_work_related_detail"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)

    # ── WFH / Remote Work ─────────────────────────────────────
    start_date          = Column(String(20), nullable=True)
    end_date            = Column(String(20), nullable=True)
    wfh_reason          = Column(Text,       nullable=True)
    is_recurring        = Column(Boolean,    default=False)
    recurrence_pattern  = Column(String(100), nullable=True)  # Daily / Weekly / specific days
    work_location_address = Column(Text,     nullable=True)

    # ── Shift Change ──────────────────────────────────────────
    current_shift       = Column(String(100), nullable=True)
    requested_shift     = Column(String(100), nullable=True)
    shift_change_reason = Column(Text,        nullable=True)
    shift_effective_date= Column(String(20),  nullable=True)

    # ── Department Transfer ───────────────────────────────────
    current_department  = Column(String(100), nullable=True)
    requested_department= Column(String(100), nullable=True)
    transfer_reason     = Column(Text,        nullable=True)
    transfer_effective_date = Column(String(20), nullable=True)
    current_manager     = Column(String(255), nullable=True)

    # ── Reporting Manager Change ──────────────────────────────
    current_reporting_manager  = Column(String(255), nullable=True)
    requested_reporting_manager= Column(String(255), nullable=True)
    manager_change_reason      = Column(Text,        nullable=True)
    manager_change_effective_date = Column(String(20), nullable=True)

    # ── Desk / Seat Change ────────────────────────────────────
    current_desk        = Column(String(100), nullable=True)
    preferred_desk      = Column(String(100), nullable=True)
    desk_change_reason  = Column(Text,        nullable=True)

    remarks             = Column(Text, nullable=True)

    request = relationship("RequestManagement", back_populates="work_related_detail")


class RequestAdminDetail(Base):
    """
    Administrative category: ID Card Reissue, Access Card, Parking Slot,
    Locker Assignment, Stationery Requisition, Business Card.
    """
    __tablename__ = "request_admin_detail"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)

    # ── ID Card Reissue ───────────────────────────────────────
    id_card_reason      = Column(String(200), nullable=True)  # Lost / Damaged / Name Change
    old_id_card_number  = Column(String(100), nullable=True)

    # ── Access Card ───────────────────────────────────────────
    access_areas        = Column(String(500), nullable=True)  # Comma-separated building areas
    access_level        = Column(String(50),  nullable=True)  # Standard / Restricted / Full
    access_start_date   = Column(String(20),  nullable=True)
    access_end_date     = Column(String(20),  nullable=True)

    # ── Parking Slot ──────────────────────────────────────────
    vehicle_type        = Column(String(50),  nullable=True)  # Car / Bike / Other
    vehicle_number      = Column(String(30),  nullable=True)
    parking_location    = Column(String(100), nullable=True)
    preferred_slot      = Column(String(30),  nullable=True)

    # ── Locker Assignment ─────────────────────────────────────
    locker_floor        = Column(String(20),  nullable=True)
    preferred_locker    = Column(String(30),  nullable=True)
    locker_reason       = Column(Text,        nullable=True)

    # ── Stationery Requisition ────────────────────────────────
    # Items stored as JSON-like text: "item:qty,item:qty"
    stationery_items    = Column(Text, nullable=True)
    cost_center         = Column(String(100), nullable=True)

    # ── Business Card ─────────────────────────────────────────
    card_name           = Column(String(255), nullable=True)
    card_designation    = Column(String(255), nullable=True)
    card_email          = Column(String(255), nullable=True)
    card_phone          = Column(String(30),  nullable=True)
    card_quantity       = Column(Integer,     nullable=True)

    remarks             = Column(Text, nullable=True)

    request = relationship("RequestManagement", back_populates="admin_detail")


class RequestFinancialDetail(Base):
    """
    Financial category: Salary Advance, Reimbursement Claim, Loan Application,
    Investment Declaration 80C, Tax Regime Change, Salary Certificate.
    """
    __tablename__ = "request_financial_detail"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)

    # ── Salary Advance ────────────────────────────────────────
    advance_amount        = Column(Numeric(12, 2), nullable=True)
    advance_reason        = Column(Text,           nullable=True)
    repayment_months      = Column(Integer,        nullable=True)
    advance_month         = Column(String(20),     nullable=True)  # "April 2025"

    # ── Reimbursement Claim ───────────────────────────────────
    expense_type          = Column(String(100), nullable=True)   # Medical / Travel / Education
    expense_date          = Column(String(20),  nullable=True)
    expense_amount        = Column(Numeric(12, 2), nullable=True)
    expense_description   = Column(Text,        nullable=True)
    bill_reference        = Column(String(200), nullable=True)

    # ── Loan Application ──────────────────────────────────────
    loan_type             = Column(String(100), nullable=True)  # Personal / Housing / Vehicle
    loan_amount           = Column(Numeric(12, 2), nullable=True)
    loan_tenure_months    = Column(Integer,     nullable=True)
    loan_purpose          = Column(Text,        nullable=True)

    # ── Investment Declaration 80C ────────────────────────────
    financial_year        = Column(String(10),  nullable=True)   # "2025-26"
    investment_type       = Column(String(200), nullable=True)   # PPF / ELSS / LIC etc.
    declared_amount       = Column(Numeric(12, 2), nullable=True)
    investment_proof_note = Column(Text,        nullable=True)

    # ── Tax Regime Change ─────────────────────────────────────
    current_regime        = Column(String(20), nullable=True)   # Old / New
    requested_regime      = Column(String(20), nullable=True)
    regime_change_reason  = Column(Text,       nullable=True)

    # ── Salary Certificate ────────────────────────────────────
    certificate_purpose   = Column(String(300), nullable=True)  # Visa / Loan / Personal
    address_to            = Column(String(500), nullable=True)  # Issuing authority name

    currency              = Column(String(10), default="INR", nullable=False)
    supporting_doc_url    = Column(Text, nullable=True)
    remarks               = Column(Text, nullable=True)

    request = relationship("RequestManagement", back_populates="financial_detail")


class RequestTravelExpenseDetail(Base):
    """
    Travel & Expense category: Business Travel, Expense Reimbursement,
    Travel Advance, Mileage Claim, Per Diem Claim.
    """
    __tablename__ = "request_travel_expense_detail"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)

    # ── Trip details (shared) ─────────────────────────────────
    travel_from         = Column(String(255), nullable=True)
    travel_to           = Column(String(255), nullable=True)
    travel_start_date   = Column(String(20),  nullable=True)
    travel_end_date     = Column(String(20),  nullable=True)
    travel_purpose      = Column(Text,        nullable=True)
    trip_type           = Column(String(50),  nullable=True)   # Domestic / International

    # ── Business Travel Request ───────────────────────────────
    transport_mode      = Column(String(50),  nullable=True)   # Air / Train / Bus / Road
    accommodation_required = Column(Boolean, default=False)
    estimated_cost      = Column(Numeric(12, 2), nullable=True)
    project_code        = Column(String(100),   nullable=True)

    # ── Expense Reimbursement ─────────────────────────────────
    expense_category    = Column(String(100), nullable=True)
    total_expense_amount= Column(Numeric(12, 2), nullable=True)
    expense_date        = Column(String(20),  nullable=True)
    receipt_reference   = Column(String(300), nullable=True)

    # ── Travel Advance ────────────────────────────────────────
    advance_amount      = Column(Numeric(12, 2), nullable=True)
    advance_required_by = Column(String(20),  nullable=True)

    # ── Mileage Claim ─────────────────────────────────────────
    vehicle_type        = Column(String(50),  nullable=True)
    start_odometer      = Column(Numeric(10, 2), nullable=True)
    end_odometer        = Column(Numeric(10, 2), nullable=True)
    total_km            = Column(Numeric(10, 2), nullable=True)
    rate_per_km         = Column(Numeric(8, 2),  nullable=True)
    mileage_amount      = Column(Numeric(12, 2), nullable=True)

    # ── Per Diem Claim ────────────────────────────────────────
    per_diem_days       = Column(Integer,     nullable=True)
    per_diem_rate       = Column(Numeric(10, 2), nullable=True)
    per_diem_amount     = Column(Numeric(12, 2), nullable=True)
    per_diem_city_tier  = Column(String(20),  nullable=True)  # Tier 1 / 2 / 3

    currency            = Column(String(10), default="INR", nullable=False)
    manager_approval_needed = Column(Boolean, default=True)
    supporting_doc_url  = Column(Text, nullable=True)
    remarks             = Column(Text, nullable=True)

    request = relationship("RequestManagement", back_populates="travel_expense_detail")


class RequestITSystemsDetail(Base):
    """
    IT & Systems category: Software Access, VPN Access, Email Distribution List,
    System/Application Access, Hardware Request.
    """
    __tablename__ = "request_it_systems_detail"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)

    # ── Software / System / Application Access ────────────────
    software_name       = Column(String(255), nullable=True)
    access_type         = Column(String(50),  nullable=True)   # Read / Write / Admin
    access_reason       = Column(Text,        nullable=True)
    access_duration     = Column(String(50),  nullable=True)   # Permanent / Temporary / "3 months"
    access_end_date     = Column(String(20),  nullable=True)
    manager_approved    = Column(Boolean,     default=False)

    # ── VPN Access ────────────────────────────────────────────
    vpn_location        = Column(String(255), nullable=True)
    vpn_reason          = Column(Text,        nullable=True)
    device_type         = Column(String(100), nullable=True)

    # ── Email Distribution List ───────────────────────────────
    distribution_list_name = Column(String(255), nullable=True)
    distribution_action    = Column(String(50),  nullable=True)  # Add / Remove / Create
    email_to_add           = Column(String(255), nullable=True)

    # ── Hardware Request ──────────────────────────────────────
    hardware_type       = Column(String(100), nullable=True)   # Laptop / Monitor / Keyboard etc.
    hardware_model      = Column(String(255), nullable=True)
    hardware_quantity   = Column(Integer,     default=1)
    hardware_reason     = Column(Text,        nullable=True)
    urgency_level       = Column(String(50),  nullable=True)

    cost_center         = Column(String(100), nullable=True)
    remarks             = Column(Text,        nullable=True)

    request = relationship("RequestManagement", back_populates="it_systems_detail")


class RequestFeedbackDetail(Base):
    """
    Feedback category: General Feedback, HR Grievance, Suggestion Box,
    POSH Complaint, Ethics Violation Reporting.
    """
    __tablename__ = "request_feedback_detail"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, unique=True, index=True)

    # Sensitivity flags
    is_anonymous        = Column(Boolean, default=False, nullable=False)
    is_confidential     = Column(Boolean, default=False, nullable=False)

    # ── General Feedback / Suggestion Box ─────────────────────
    feedback_category   = Column(String(100), nullable=True)  # Workplace / Process / Culture
    feedback_rating     = Column(Integer,     nullable=True)  # 1-5 scale

    # ── HR Grievance ──────────────────────────────────────────
    grievance_against   = Column(String(255), nullable=True)
    incident_date       = Column(String(20),  nullable=True)
    incident_location   = Column(String(255), nullable=True)
    previous_escalations= Column(Boolean,     default=False)

    # ── POSH Complaint ────────────────────────────────────────
    accused_name        = Column(String(255), nullable=True)
    accused_designation = Column(String(255), nullable=True)
    incident_description= Column(Text,        nullable=True)
    witness_names       = Column(Text,        nullable=True)   # comma-separated
    posh_report_date    = Column(String(20),  nullable=True)

    # ── Ethics Violation Reporting ────────────────────────────
    violation_type      = Column(String(200), nullable=True)   # Fraud / Bribery / Data Breach
    persons_involved    = Column(Text,        nullable=True)
    evidence_description= Column(Text,        nullable=True)

    # Case management
    case_number         = Column(String(50),  nullable=True)   # filled after case is registered
    assigned_investigator = Column(String(255), nullable=True)
    resolution_summary  = Column(Text,        nullable=True)

    remarks             = Column(Text, nullable=True)

    request = relationship("RequestManagement", back_populates="feedback_detail")


# ─────────────────────────────────────────────────────────────────────────────
# SUPPORTING TABLES
# ─────────────────────────────────────────────────────────────────────────────

class RequestComment(Base):
    """Thread of comments / notes on a request."""
    __tablename__ = "request_comments"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id  = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    author_id   = Column(Integer,  ForeignKey("users.id"), nullable=True)
    author_name = Column(String(255), nullable=True)
    body        = Column(Text, nullable=False)
    is_internal = Column(Boolean, default=False)  # internal HR note vs employee-visible
    created_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    request = relationship("RequestManagement", back_populates="comments")

    __table_args__ = (
        Index("ix_req_comment_request", "request_id"),
    )


class RequestAttachment(Base):
    """Files uploaded with or after request submission."""
    __tablename__ = "request_attachments"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id      = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                              nullable=False, index=True)
    file_name       = Column(String(500), nullable=False)
    file_url        = Column(Text,        nullable=False)
    file_size_bytes = Column(BigInteger,  nullable=True)
    mime_type       = Column(String(100), nullable=True)
    uploaded_by     = Column(String(255), nullable=True)
    uploaded_at     = Column(DateTime, default=datetime.utcnow, nullable=False)

    request = relationship("RequestManagement", back_populates="attachments")

    __table_args__ = (
        Index("ix_req_attachment_request", "request_id"),
    )


class RequestStatusLog(Base):
    """Immutable audit trail of every status change."""
    __tablename__ = "request_status_logs"

    id          = Column(Integer, primary_key=True, index=True, autoincrement=True)
    request_id  = Column(BigInteger, ForeignKey("request_management.id", ondelete="CASCADE"),
                          nullable=False, index=True)
    from_status = Column(String(50), nullable=True)
    to_status   = Column(String(50), nullable=False)
    changed_by  = Column(String(255), nullable=True)
    changed_by_id = Column(Integer,   ForeignKey("users.id"), nullable=True)
    note        = Column(Text,        nullable=True)
    changed_at  = Column(DateTime, default=datetime.utcnow, nullable=False)

    request = relationship("RequestManagement", back_populates="status_logs")

    __table_args__ = (
        Index("ix_req_status_log_request", "request_id"),
    )


class RequestTypeConfig(Base):
    """
    Admin-configurable metadata per request type — SLA, priority, workflow,
    auto-description template, and availability settings.
    Allows HR admins to customise behaviour without code changes.
    """
    __tablename__ = "request_type_config"

    id              = Column(Integer, primary_key=True, index=True, autoincrement=True)
    category        = Column(String(50),  nullable=False, index=True)
    request_type    = Column(String(100), nullable=False, unique=True, index=True)
    display_name    = Column(String(200), nullable=False)
    description     = Column(Text,        nullable=True)
    default_priority= Column(String(20),  nullable=False, default=RequestPriority.MEDIUM)
    sla_days        = Column(String(50),  nullable=True)
    workflow_id     = Column(Integer, ForeignKey("workflows.id"), nullable=True)
    auto_description_template = Column(Text, nullable=True)
    is_active       = Column(Boolean, default=True, nullable=False)
    requires_attachment = Column(Boolean, default=False, nullable=False)
    requires_manager_approval = Column(Boolean, default=False, nullable=False)

    created_at      = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at      = Column(DateTime, default=datetime.utcnow,
                             onupdate=datetime.utcnow, nullable=False)

    workflow = relationship("Workflow", foreign_keys=[workflow_id])

    __table_args__ = (
        Index("ix_rtc_category_active", "category", "is_active"),
    )
