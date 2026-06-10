from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import Column, Integer, String, Boolean, Float, DateTime, Text, ForeignKey
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime, date, timedelta
from enum import Enum

from core.database import Base, get_db

# ──────────────────────────────────────────
# ENUMS
# ──────────────────────────────────────────

class NoticePeriodUnit(str, Enum):
    DAYS = "days"
    WEEKS = "weeks"
    MONTHS = "months"

class NoticePeriodStatus(str, Enum):
    ACTIVE = "active"
    INACTIVE = "inactive"

class NoticeRequestStatus(str, Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    WAIVED = "waived"
    COMPLETED = "completed"

class NoticeType(str, Enum):
    RESIGNATION = "resignation"
    TERMINATION = "termination"
    RETIREMENT = "retirement"
    CONTRACT_END = "contract_end"

# ──────────────────────────────────────────
# MODELS
# ──────────────────────────────────────────

class NoticePeriodPolicy(Base):
    """
    Defines notice period rules per designation / employment type.
    """
    __tablename__ = "notice_period_policies"

    id                  = Column(Integer, primary_key=True, index=True)
    policy_name         = Column(String(100), nullable=False, unique=True)
    designation         = Column(String(100), nullable=True)   # NULL = applies to all
    employment_type     = Column(String(50),  nullable=True)   # Full-time, Contract, etc.
    department          = Column(String(100), nullable=True)
    notice_duration     = Column(Integer, nullable=False)       # numeric value
    notice_unit         = Column(String(20),  nullable=False, default=NoticePeriodUnit.DAYS)
    min_notice_duration = Column(Integer, nullable=True)        # for waivers
    max_notice_duration = Column(Integer, nullable=True)
    is_negotiable       = Column(Boolean, default=False)
    buyout_allowed      = Column(Boolean, default=False)
    buyout_rate_per_day = Column(Float,   nullable=True)        # salary/day for buyout
    description         = Column(Text,    nullable=True)
    status              = Column(String(20), default=NoticePeriodStatus.ACTIVE)
    created_at          = Column(DateTime, default=datetime.utcnow)
    updated_at          = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class NoticeRequest(Base):
    """
    Tracks an individual employee's notice period request / event.
    """
    __tablename__ = "notice_requests"

    id                   = Column(Integer, primary_key=True, index=True)
    employee_id          = Column(Integer, nullable=False, index=True)
    policy_id            = Column(Integer, ForeignKey("notice_period_policies.id"), nullable=True)
    notice_type          = Column(String(30), nullable=False)
    notice_date          = Column(DateTime, nullable=False)      # date notice was given
    expected_last_date   = Column(DateTime, nullable=False)      # auto-calculated
    actual_last_date     = Column(DateTime, nullable=True)       # after approval/completion
    waiver_requested     = Column(Boolean, default=False)
    waiver_reason        = Column(Text, nullable=True)
    waiver_approved_by   = Column(Integer, nullable=True)        # HR user id
    buyout_requested     = Column(Boolean, default=False)
    buyout_amount        = Column(Float, nullable=True)
    buyout_approved      = Column(Boolean, default=False)
    status               = Column(String(30), default=NoticeRequestStatus.PENDING)
    remarks              = Column(Text, nullable=True)
    approved_by          = Column(Integer, nullable=True)
    approved_at          = Column(DateTime, nullable=True)
    created_at           = Column(DateTime, default=datetime.utcnow)
    updated_at           = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# ──────────────────────────────────────────
# SCHEMAS  (Pydantic)
# ──────────────────────────────────────────

# --- Policy schemas ---

class NoticePeriodPolicyBase(BaseModel):
    policy_name         : str           = Field(..., max_length=100)
    designation         : Optional[str] = None
    employment_type     : Optional[str] = None
    department          : Optional[str] = None
    notice_duration     : int           = Field(..., gt=0)
    notice_unit         : NoticePeriodUnit = NoticePeriodUnit.DAYS
    min_notice_duration : Optional[int] = None
    max_notice_duration : Optional[int] = None
    is_negotiable       : bool          = False
    buyout_allowed      : bool          = False
    buyout_rate_per_day : Optional[float] = None
    description         : Optional[str] = None
    status              : NoticePeriodStatus = NoticePeriodStatus.ACTIVE

    @validator("max_notice_duration")
    def max_gte_min(cls, v, values):
        mn = values.get("min_notice_duration")
        if v is not None and mn is not None and v < mn:
            raise ValueError("max_notice_duration must be >= min_notice_duration")
        return v

    @validator("buyout_rate_per_day")
    def buyout_rate_required_when_allowed(cls, v, values):
        if values.get("buyout_allowed") and v is None:
            raise ValueError("buyout_rate_per_day is required when buyout_allowed is True")
        return v

class NoticePeriodPolicyCreate(NoticePeriodPolicyBase):
    pass

class NoticePeriodPolicyUpdate(BaseModel):
    policy_name         : Optional[str]               = None
    designation         : Optional[str]               = None
    employment_type     : Optional[str]               = None
    department          : Optional[str]               = None
    notice_duration     : Optional[int]               = Field(None, gt=0)
    notice_unit         : Optional[NoticePeriodUnit]  = None
    min_notice_duration : Optional[int]               = None
    max_notice_duration : Optional[int]               = None
    is_negotiable       : Optional[bool]              = None
    buyout_allowed      : Optional[bool]              = None
    buyout_rate_per_day : Optional[float]             = None
    description         : Optional[str]               = None
    status              : Optional[NoticePeriodStatus] = None

class NoticePeriodPolicyResponse(NoticePeriodPolicyBase):
    id         : int
    created_at : datetime
    updated_at : datetime

    class Config:
        from_attributes = True

# --- Notice Request schemas ---

class NoticeRequestBase(BaseModel):
    employee_id      : int
    policy_id        : Optional[int]  = None
    notice_type      : NoticeType
    notice_date      : datetime
    waiver_requested : bool           = False
    waiver_reason    : Optional[str]  = None
    buyout_requested : bool           = False
    remarks          : Optional[str]  = None

class NoticeRequestCreate(NoticeRequestBase):
    pass

class NoticeRequestUpdate(BaseModel):
    actual_last_date   : Optional[datetime] = None
    waiver_requested   : Optional[bool]     = None
    waiver_reason      : Optional[str]      = None
    waiver_approved_by : Optional[int]      = None
    buyout_requested   : Optional[bool]     = None
    buyout_amount      : Optional[float]    = None
    buyout_approved    : Optional[bool]     = None
    status             : Optional[NoticeRequestStatus] = None
    remarks            : Optional[str]      = None
    approved_by        : Optional[int]      = None

class NoticeRequestResponse(NoticeRequestBase):
    id                 : int
    expected_last_date : datetime
    actual_last_date   : Optional[datetime]
    buyout_amount      : Optional[float]
    buyout_approved    : bool
    waiver_approved_by : Optional[int]
    status             : NoticeRequestStatus
    approved_by        : Optional[int]
    approved_at        : Optional[datetime]
    created_at         : datetime
    updated_at         : datetime

    class Config:
        from_attributes = True

class NoticeRequestApproval(BaseModel):
    status             : NoticeRequestStatus
    approved_by        : int
    actual_last_date   : Optional[datetime] = None
    remarks            : Optional[str]      = None
    waiver_approved_by : Optional[int]      = None
    buyout_approved    : Optional[bool]     = None
    buyout_amount      : Optional[float]    = None

# ──────────────────────────────────────────
# HELPER  – calculate last working date
# ──────────────────────────────────────────

def calculate_last_date(
    notice_date: datetime,
    duration: int,
    unit: str
) -> datetime:
    """Return expected last working date from notice date + policy duration."""
    if unit == NoticePeriodUnit.DAYS:
        return notice_date + timedelta(days=duration)
    elif unit == NoticePeriodUnit.WEEKS:
        return notice_date + timedelta(weeks=duration)
    elif unit == NoticePeriodUnit.MONTHS:
        # approximate: 30 days per month
        return notice_date + timedelta(days=duration * 30)
    return notice_date + timedelta(days=duration)

# ──────────────────────────────────────────
# ROUTER
# ──────────────────────────────────────────

router = APIRouter(
    prefix="/hr-operations/notice-period",
    tags=["HR Operations - Notice Period"],
)

# ════════════════════════════════════════
# POLICY  endpoints
# ════════════════════════════════════════

@router.post(
    "/policies",
    response_model=NoticePeriodPolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new notice period policy",
)
def create_policy(
    payload: NoticePeriodPolicyCreate,
    db: Session = Depends(get_db),
):
    # Check duplicate name
    existing = (
        db.query(NoticePeriodPolicy)
        .filter(NoticePeriodPolicy.policy_name == payload.policy_name)
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Policy with name '{payload.policy_name}' already exists.",
        )

    policy = NoticePeriodPolicy(**payload.dict())
    db.add(policy)
    db.commit()
    db.refresh(policy)
    return policy


@router.get(
    "/policies",
    response_model=List[NoticePeriodPolicyResponse],
    summary="List all notice period policies",
)
def list_policies(
    status_filter : Optional[str] = None,
    designation   : Optional[str] = None,
    department    : Optional[str] = None,
    skip          : int           = 0,
    limit         : int           = 100,
    db            : Session       = Depends(get_db),
):
    query = db.query(NoticePeriodPolicy)

    if status_filter:
        query = query.filter(NoticePeriodPolicy.status == status_filter)
    if designation:
        query = query.filter(NoticePeriodPolicy.designation == designation)
    if department:
        query = query.filter(NoticePeriodPolicy.department == department)

    return query.offset(skip).limit(limit).all()


@router.get(
    "/policies/{policy_id}",
    response_model=NoticePeriodPolicyResponse,
    summary="Get a notice period policy by ID",
)
def get_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(NoticePeriodPolicy).filter(NoticePeriodPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with id {policy_id} not found.",
        )
    return policy


@router.put(
    "/policies/{policy_id}",
    response_model=NoticePeriodPolicyResponse,
    summary="Update a notice period policy",
)
def update_policy(
    policy_id: int,
    payload  : NoticePeriodPolicyUpdate,
    db       : Session = Depends(get_db),
):
    policy = db.query(NoticePeriodPolicy).filter(NoticePeriodPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with id {policy_id} not found.",
        )

    update_data = payload.dict(exclude_unset=True)

    # Duplicate name check if name is being changed
    if "policy_name" in update_data and update_data["policy_name"] != policy.policy_name:
        dup = (
            db.query(NoticePeriodPolicy)
            .filter(NoticePeriodPolicy.policy_name == update_data["policy_name"])
            .first()
        )
        if dup:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Policy name '{update_data['policy_name']}' is already taken.",
            )

    for field, value in update_data.items():
        setattr(policy, field, value)

    policy.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(policy)
    return policy


@router.delete(
    "/policies/{policy_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete (deactivate) a notice period policy",
)
def delete_policy(policy_id: int, db: Session = Depends(get_db)):
    policy = db.query(NoticePeriodPolicy).filter(NoticePeriodPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with id {policy_id} not found.",
        )
    # Soft delete — mark inactive rather than hard delete
    policy.status     = NoticePeriodStatus.INACTIVE
    policy.updated_at = datetime.utcnow()
    db.commit()


# ════════════════════════════════════════
# NOTICE REQUEST  endpoints
# ════════════════════════════════════════

@router.post(
    "/requests",
    response_model=NoticeRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit a notice period request for an employee",
)
def create_notice_request(
    payload: NoticeRequestCreate,
    db     : Session = Depends(get_db),
):
    # Validate policy exists when provided
    policy = None
    if payload.policy_id:
        policy = db.query(NoticePeriodPolicy).filter(
            NoticePeriodPolicy.id     == payload.policy_id,
            NoticePeriodPolicy.status == NoticePeriodStatus.ACTIVE,
        ).first()
        if not policy:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Active policy with id {payload.policy_id} not found.",
            )

    # Prevent duplicate active notice for same employee
    active_notice = db.query(NoticeRequest).filter(
        NoticeRequest.employee_id == payload.employee_id,
        NoticeRequest.status.in_([
            NoticeRequestStatus.PENDING,
            NoticeRequestStatus.APPROVED,
        ]),
    ).first()
    if active_notice:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Employee already has an active notice period request.",
        )

    # Auto-calculate expected last date from policy
    if policy:
        expected_last_date = calculate_last_date(
            payload.notice_date,
            policy.notice_duration,
            policy.notice_unit,
        )
    else:
        # Default: 30 days if no policy linked
        expected_last_date = payload.notice_date + timedelta(days=30)

    notice = NoticeRequest(
        **payload.dict(),
        expected_last_date=expected_last_date,
    )
    db.add(notice)
    db.commit()
    db.refresh(notice)
    return notice


@router.get(
    "/requests",
    response_model=List[NoticeRequestResponse],
    summary="List all notice period requests",
)
def list_notice_requests(
    employee_id   : Optional[int] = None,
    status_filter : Optional[str] = None,
    notice_type   : Optional[str] = None,
    skip          : int           = 0,
    limit         : int           = 100,
    db            : Session       = Depends(get_db),
):
    query = db.query(NoticeRequest)

    if employee_id:
        query = query.filter(NoticeRequest.employee_id == employee_id)
    if status_filter:
        query = query.filter(NoticeRequest.status == status_filter)
    if notice_type:
        query = query.filter(NoticeRequest.notice_type == notice_type)

    return query.order_by(NoticeRequest.created_at.desc()).offset(skip).limit(limit).all()


@router.get(
    "/requests/{request_id}",
    response_model=NoticeRequestResponse,
    summary="Get a specific notice period request",
)
def get_notice_request(request_id: int, db: Session = Depends(get_db)):
    notice = db.query(NoticeRequest).filter(NoticeRequest.id == request_id).first()
    if not notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notice request with id {request_id} not found.",
        )
    return notice


@router.put(
    "/requests/{request_id}",
    response_model=NoticeRequestResponse,
    summary="Update a notice period request",
)
def update_notice_request(
    request_id: int,
    payload   : NoticeRequestUpdate,
    db        : Session = Depends(get_db),
):
    notice = db.query(NoticeRequest).filter(NoticeRequest.id == request_id).first()
    if not notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notice request with id {request_id} not found.",
        )

    if notice.status == NoticeRequestStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot update a completed notice request.",
        )

    update_data = payload.dict(exclude_unset=True)
    for field, value in update_data.items():
        setattr(notice, field, value)

    notice.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(notice)
    return notice


@router.patch(
    "/requests/{request_id}/approval",
    response_model=NoticeRequestResponse,
    summary="Approve / reject / waive a notice period request",
)
def approve_notice_request(
    request_id: int,
    payload   : NoticeRequestApproval,
    db        : Session = Depends(get_db),
):
    notice = db.query(NoticeRequest).filter(NoticeRequest.id == request_id).first()
    if not notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notice request with id {request_id} not found.",
        )

    if notice.status in [NoticeRequestStatus.COMPLETED, NoticeRequestStatus.REJECTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Notice request is already '{notice.status}' and cannot be changed.",
        )

    notice.status      = payload.status
    notice.approved_by = payload.approved_by
    notice.approved_at = datetime.utcnow()
    notice.updated_at  = datetime.utcnow()

    if payload.remarks:
        notice.remarks = payload.remarks
    if payload.actual_last_date:
        notice.actual_last_date = payload.actual_last_date
    if payload.waiver_approved_by:
        notice.waiver_approved_by = payload.waiver_approved_by
    if payload.buyout_approved is not None:
        notice.buyout_approved = payload.buyout_approved
    if payload.buyout_amount is not None:
        notice.buyout_amount = payload.buyout_amount

    db.commit()
    db.refresh(notice)
    return notice


@router.delete(
    "/requests/{request_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Cancel / delete a pending notice period request",
)
def cancel_notice_request(request_id: int, db: Session = Depends(get_db)):
    notice = db.query(NoticeRequest).filter(NoticeRequest.id == request_id).first()
    if not notice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Notice request with id {request_id} not found.",
        )

    if notice.status != NoticeRequestStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending notice requests can be cancelled.",
        )

    db.delete(notice)
    db.commit()


# ════════════════════════════════════════
# UTILITY  endpoint
# ════════════════════════════════════════

@router.get(
    "/calculate-last-date",
    summary="Calculate expected last working date from a given notice date + policy",
)
def calculate_last_working_date(
    policy_id   : int,
    notice_date : date,
    db          : Session = Depends(get_db),
):
    """Utility – pass a policy_id and notice_date to get the expected last date."""
    policy = db.query(NoticePeriodPolicy).filter(NoticePeriodPolicy.id == policy_id).first()
    if not policy:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Policy with id {policy_id} not found.",
        )

    notice_dt      = datetime.combine(notice_date, datetime.min.time())
    last_date      = calculate_last_date(notice_dt, policy.notice_duration, policy.notice_unit)

    return {
        "policy_id"          : policy_id,
        "policy_name"        : policy.policy_name,
        "notice_date"        : notice_date.isoformat(),
        "notice_duration"    : policy.notice_duration,
        "notice_unit"        : policy.notice_unit,
        "expected_last_date" : last_date.date().isoformat(),
    }
