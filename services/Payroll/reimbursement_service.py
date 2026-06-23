from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List, Optional
from datetime import date, datetime, timezone
import calendar

from model.Payroll.reimbursement import (
    ReimbursementType,
    ReimbursementClaim,
    ReimbursementBalance,
)
from schema.Payroll.reimbursement import (
    ReimbursementTypeCreate,
    ReimbursementTypeUpdate,
    ReimbursementClaimCreate,
    ReimbursementClaimUpdate,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _get_period(frequency: str) -> str:
    """Return current period string based on frequency."""
    today = date.today()
    if frequency == "Monthly":
        return today.strftime("%Y-%m")       # "2024-04"
    elif frequency == "Quarterly":
        q = (today.month - 1) // 3 + 1
        return f"{today.year}-Q{q}"          # "2024-Q2"
    else:                                    # Yearly / Ad-hoc
        return str(today.year)               # "2024"


def _ensure_balance(
    db: Session,
    employee_id: int,
    rtype: ReimbursementType,
) -> ReimbursementBalance:
    """Get or create a balance record for this employee + type + period."""
    period = _get_period(rtype.frequency)
    balance = (
        db.query(ReimbursementBalance)
        .filter(
            ReimbursementBalance.employee_id == employee_id,
            ReimbursementBalance.reimbursement_type_id == rtype.id,
            ReimbursementBalance.period == period,
        )
        .first()
    )
    if not balance:
        balance = ReimbursementBalance(
            employee_id           = employee_id,
            reimbursement_type_id = rtype.id,
            period                = period,
            limit_amount          = rtype.limit_amount,
            used_amount           = 0.0,
            remaining_amount      = rtype.limit_amount,
        )
        db.add(balance)
        db.flush()
    return balance


# ── Reimbursement Type (Master) ───────────────────────────────────────────────

def get_all_types(db: Session, is_active: Optional[bool] = None):
    q = db.query(ReimbursementType)
    if is_active is not None:
        q = q.filter(ReimbursementType.is_active == is_active)
    return q.order_by(ReimbursementType.id.asc()).all()


def get_type_by_id(db: Session, type_id: int):
    return db.query(ReimbursementType).filter(ReimbursementType.id == type_id).first()


def create_type(db: Session, payload: ReimbursementTypeCreate):
    rtype = ReimbursementType(**payload.model_dump())
    db.add(rtype)
    db.commit()
    db.refresh(rtype)
    return rtype


def update_type(db: Session, type_id: int, payload: ReimbursementTypeUpdate):
    rtype = get_type_by_id(db, type_id)
    if not rtype:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(rtype, key, value)
    db.commit()
    db.refresh(rtype)
    return rtype


def delete_type(db: Session, type_id: int):
    rtype = get_type_by_id(db, type_id)
    if not rtype:
        return False
    rtype.is_active = False
    db.commit()
    return True


# ── Reimbursement Claims ──────────────────────────────────────────────────────

def get_all_claims(
    db: Session,
    status: Optional[str]      = None,
    claim_type_id: Optional[int] = None,
    employee_id: Optional[int] = None,
    search: Optional[str]      = None,
):
    q = db.query(ReimbursementClaim)
    if status:
        q = q.filter(ReimbursementClaim.status == status.upper())
    if claim_type_id:
        q = q.filter(ReimbursementClaim.reimbursement_type_id == claim_type_id)
    if employee_id:
        q = q.filter(ReimbursementClaim.employee_id == employee_id)
    return q.order_by(ReimbursementClaim.id.desc()).all()


def get_claim_by_id(db: Session, claim_id: int):
    return db.query(ReimbursementClaim).filter(ReimbursementClaim.id == claim_id).first()


def create_claim(db: Session, payload: ReimbursementClaimCreate):
    rtype = get_type_by_id(db, payload.reimbursement_type_id)
    if not rtype:
        return None, "Reimbursement type not found"

    # Check balance limit
    balance = _ensure_balance(db, payload.employee_id, rtype)
    if payload.amount > balance.remaining_amount:
        return None, f"Amount exceeds remaining balance of ₹{balance.remaining_amount}"

    # Calculate tax
    tax_amount = round(payload.amount * 0.10, 2) if rtype.is_taxable else 0.0

    claim = ReimbursementClaim(
        **payload.model_dump(),
        status     = "PENDING",
        is_taxable = rtype.is_taxable,
        tax_amount = tax_amount,
    )
    db.add(claim)
    db.commit()
    db.refresh(claim)
    return claim, None


def update_claim(db: Session, claim_id: int, payload: ReimbursementClaimUpdate):
    claim = get_claim_by_id(db, claim_id)
    if not claim:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(claim, key, value)
    db.commit()
    db.refresh(claim)
    return claim


def delete_claim(db: Session, claim_id: int):
    claim = get_claim_by_id(db, claim_id)
    if not claim:
        return False
    db.delete(claim)
    db.commit()
    return True


# ── Approval workflow ─────────────────────────────────────────────────────────

def manager_approve(
    db: Session,
    claim_id: int,
    approved_by: Optional[str],
    remarks: Optional[str],
):
    claim = get_claim_by_id(db, claim_id)
    if not claim:
        return None, "Claim not found"
    if claim.manager_status == "APPROVED":
        return None, "Already approved by manager"

    claim.manager_status        = "APPROVED"
    claim.manager_approved_by   = approved_by
    claim.manager_approved_date = date.today()
    claim.manager_remarks       = remarks
    claim.status                = "FINANCE_REVIEW"

    db.commit()
    db.refresh(claim)
    return claim, None


def manager_reject(
    db: Session,
    claim_id: int,
    approved_by: Optional[str],
    remarks: Optional[str],
):
    claim = get_claim_by_id(db, claim_id)
    if not claim:
        return None, "Claim not found"

    claim.manager_status        = "REJECTED"
    claim.manager_approved_by   = approved_by
    claim.manager_approved_date = date.today()
    claim.manager_remarks       = remarks
    claim.status                = "REJECTED"

    db.commit()
    db.refresh(claim)
    return claim, None


def finance_approve(
    db: Session,
    claim_id: int,
    approved_by: Optional[str],
    remarks: Optional[str],
):
    claim = get_claim_by_id(db, claim_id)
    if not claim:
        return None, "Claim not found"
    if claim.manager_status != "APPROVED":
        return None, "Manager must approve before Finance"
    if claim.finance_status == "APPROVED":
        return None, "Already approved by Finance"

    claim.finance_status        = "APPROVED"
    claim.finance_approved_by   = approved_by
    claim.finance_approved_date = date.today()
    claim.finance_remarks       = remarks
    claim.status                = "APPROVED"

    # Deduct from balance
    rtype   = get_type_by_id(db, claim.reimbursement_type_id)
    balance = _ensure_balance(db, claim.employee_id, rtype)
    balance.used_amount      = round(balance.used_amount + claim.amount, 2)
    balance.remaining_amount = round(balance.limit_amount - balance.used_amount, 2)

    db.commit()
    db.refresh(claim)
    return claim, None


def finance_reject(
    db: Session,
    claim_id: int,
    approved_by: Optional[str],
    remarks: Optional[str],
):
    claim = get_claim_by_id(db, claim_id)
    if not claim:
        return None, "Claim not found"

    claim.finance_status        = "REJECTED"
    claim.finance_approved_by   = approved_by
    claim.finance_approved_date = date.today()
    claim.finance_remarks       = remarks
    claim.status                = "REJECTED"

    db.commit()
    db.refresh(claim)
    return claim, None


# ── Balances ──────────────────────────────────────────────────────────────────

def get_balances(db: Session, employee_id: Optional[int] = None):
    q = db.query(ReimbursementBalance)
    if employee_id:
        q = q.filter(ReimbursementBalance.employee_id == employee_id)
    return q.order_by(
        ReimbursementBalance.employee_id.asc(),
        ReimbursementBalance.reimbursement_type_id.asc(),
    ).all()


# ── Dashboard ─────────────────────────────────────────────────────────────────

def get_dashboard(db: Session):
    claims = db.query(ReimbursementClaim).all()

    total_claims    = len(claims)
    total_amount    = round(sum(c.amount for c in claims), 2)
    approved        = [c for c in claims if c.status == "APPROVED"]
    pending         = [c for c in claims if c.status in ("PENDING", "FINANCE_REVIEW")]
    tax_amount      = round(sum(c.tax_amount for c in claims if c.is_taxable), 2)

    return {
        "total_claims"    : total_claims,
        "total_amount"    : total_amount,
        "approved"        : len(approved),
        "approved_amount" : round(sum(c.amount for c in approved), 2),
        "pending"         : len(pending),
        "pending_amount"  : round(sum(c.amount for c in pending), 2),
        "tax_amount"      : tax_amount,
    }


# ── Reports ───────────────────────────────────────────────────────────────────

def get_reports(db: Session):
    claims = db.query(ReimbursementClaim).all()
    types  = get_all_types(db)

    # Claims by type
    claims_by_type = []
    for rtype in types:
        type_claims = [c for c in claims if c.reimbursement_type_id == rtype.id]
        count        = len(type_claims)
        total_amount = round(sum(c.amount for c in type_claims), 2)
        avg_amount   = round(total_amount / count, 2) if count else 0.0
        claims_by_type.append({
            "reimbursement_type_id": rtype.id,
            "component"            : rtype.component,
            "category"             : rtype.category,
            "count"                : count,
            "total_amount"         : total_amount,
            "avg_amount"           : avg_amount,
        })

    # Tax analysis
    taxable_claims     = [c for c in claims if c.is_taxable]
    non_taxable_claims = [c for c in claims if not c.is_taxable]
    tax_analysis = {
        "total_taxable_amount"    : round(sum(c.amount for c in taxable_claims), 2),
        "total_tax_amount"        : round(sum(c.tax_amount for c in taxable_claims), 2),
        "total_non_taxable_amount": round(sum(c.amount for c in non_taxable_claims), 2),
    }

    # Monthly trend — last 12 months
    monthly_trend = []
    today = date.today()
    for i in range(11, -1, -1):
        m = (today.month - i - 1) % 12 + 1
        y = today.year - ((today.month - i - 1) // 12 + (1 if (today.month - i - 1) < 0 else 0))
        month_name = f"{calendar.month_name[m]} {y}"
        month_claims = [
            c for c in claims
            if c.claim_date.month == m and c.claim_date.year == y
        ]
        monthly_trend.append({
            "month"       : month_name,
            "claims"      : len(month_claims),
            "total_amount": round(sum(c.amount for c in month_claims), 2),
            "approved"    : len([c for c in month_claims if c.status == "APPROVED"]),
            "pending"     : len([c for c in month_claims if c.status in ("PENDING", "FINANCE_REVIEW")]),
            "rejected"    : len([c for c in month_claims if c.status == "REJECTED"]),
        })

    return {
        "claims_by_type": claims_by_type,
        "tax_analysis"  : tax_analysis,
        "monthly_trend" : monthly_trend,
    }