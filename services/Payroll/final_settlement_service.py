from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, timezone

from model.Payroll.final_settlement import (
    FinalSettlement,
    SettlementAddition,
    SettlementDeduction,
)
from schema.Payroll.final_settlement import (
    FinalSettlementCreate,
    FinalSettlementUpdate,
    SettlementAdditionCreate,
    SettlementAdditionUpdate,
    SettlementDeductionCreate,
    SettlementDeductionUpdate,
    SettlementApproveRequest,
    SettlementRejectRequest,
    SettlementPayRequest,
)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _generate_settlement_number(db: Session) -> str:
    count = db.query(FinalSettlement).count()
    return f"FS-2024-{str(count + 1).zfill(4)}"


def _recalculate_totals(db: Session, settlement: FinalSettlement) -> FinalSettlement:
    """Recompute total_additions, total_deductions, net_settlement from line items."""
    total_additions = sum(a.amount for a in settlement.additions)
    total_deductions = sum(d.amount for d in settlement.deductions)
    net_settlement = round(
        settlement.current_settlement + total_additions - total_deductions, 2
    )
    settlement.total_additions  = round(total_additions, 2)
    settlement.total_deductions = round(total_deductions, 2)
    settlement.net_settlement   = net_settlement
    db.commit()
    db.refresh(settlement)
    return settlement


def _get_by_id(db: Session, settlement_id: int) -> Optional[FinalSettlement]:
    return db.query(FinalSettlement).filter(
        FinalSettlement.id == settlement_id
    ).first()


# ══════════════════════════════════════════════════════════════════════════════
#  Final Settlement CRUD
# ══════════════════════════════════════════════════════════════════════════════

def get_all(
    db: Session,
    status: Optional[str]      = None,
    employee_id: Optional[int] = None,
) -> List[FinalSettlement]:
    q = db.query(FinalSettlement)
    if status:
        q = q.filter(FinalSettlement.status == status.upper())
    if employee_id:
        q = q.filter(FinalSettlement.employee_id == employee_id)
    return q.order_by(FinalSettlement.id.desc()).all()


def get_by_id(db: Session, settlement_id: int) -> Optional[FinalSettlement]:
    return _get_by_id(db, settlement_id)


def get_by_employee(db: Session, employee_id: int) -> Optional[FinalSettlement]:
    """An employee can have only one active settlement at a time."""
    return (
        db.query(FinalSettlement)
        .filter(FinalSettlement.employee_id == employee_id)
        .order_by(FinalSettlement.id.desc())
        .first()
    )


def create(db: Session, payload: FinalSettlementCreate) -> FinalSettlement:
    data = payload.model_dump()
    data["settlement_number"] = _generate_settlement_number(db)
    data["status"]            = "PENDING"
    data["total_additions"]   = 0.0
    data["total_deductions"]  = 0.0
    data["net_settlement"]    = data["current_settlement"]

    settlement = FinalSettlement(**data)
    db.add(settlement)
    db.commit()
    db.refresh(settlement)
    return settlement


def update(
    db: Session,
    settlement_id: int,
    payload: FinalSettlementUpdate,
) -> Optional[FinalSettlement]:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(settlement, key, value)
    db.commit()
    db.refresh(settlement)
    return settlement


def delete(db: Session, settlement_id: int) -> bool:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return False
    db.delete(settlement)
    db.commit()
    return True


def recalculate(db: Session, settlement_id: int):
    """Recalculate button — recompute all totals from line items."""
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None, "Settlement not found"
    settlement = _recalculate_totals(db, settlement)
    return settlement, None


# ══════════════════════════════════════════════════════════════════════════════
#  Workflow — Approve / Reject / Pay
# ══════════════════════════════════════════════════════════════════════════════

def approve(
    db: Session,
    settlement_id: int,
    payload: SettlementApproveRequest,
) -> tuple:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None, "Settlement not found"
    if settlement.status == "APPROVED":
        return None, "Settlement is already approved"
    if settlement.status not in ("PENDING",):
        return None, f"Cannot approve a settlement in {settlement.status} status"

    settlement.status      = "APPROVED"
    settlement.approved_by = payload.approved_by
    settlement.approved_at = datetime.now(timezone.utc)
    if payload.remarks:
        settlement.remarks = payload.remarks

    db.commit()
    db.refresh(settlement)
    return settlement, None


def reject(
    db: Session,
    settlement_id: int,
    payload: SettlementRejectRequest,
) -> tuple:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None, "Settlement not found"
    if settlement.status == "REJECTED":
        return None, "Settlement is already rejected"
    if settlement.status == "PAID":
        return None, "Cannot reject a paid settlement"

    settlement.status           = "REJECTED"
    settlement.rejected_by      = payload.rejected_by
    settlement.rejected_at      = datetime.now(timezone.utc)
    settlement.rejection_reason = payload.rejection_reason

    db.commit()
    db.refresh(settlement)
    return settlement, None


def mark_paid(
    db: Session,
    settlement_id: int,
    payload: SettlementPayRequest,
) -> tuple:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None, "Settlement not found"
    if settlement.status != "APPROVED":
        return None, "Only APPROVED settlements can be marked as paid"

    settlement.status                 = "PAID"
    settlement.payment_mode           = payload.payment_mode
    settlement.payment_reference      = payload.payment_reference
    settlement.paid_at                = datetime.now(timezone.utc)
    settlement.payment_processing_date = datetime.now(timezone.utc).date()
    if payload.remarks:
        settlement.remarks = payload.remarks

    db.commit()
    db.refresh(settlement)
    return settlement, None


# ══════════════════════════════════════════════════════════════════════════════
#  Additions
# ══════════════════════════════════════════════════════════════════════════════

def get_additions(db: Session, settlement_id: int) -> List[SettlementAddition]:
    return (
        db.query(SettlementAddition)
        .filter(SettlementAddition.settlement_id == settlement_id)
        .order_by(SettlementAddition.id.asc())
        .all()
    )


def add_addition(
    db: Session,
    settlement_id: int,
    payload: SettlementAdditionCreate,
) -> tuple:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None, "Settlement not found"

    addition = SettlementAddition(settlement_id=settlement_id, **payload.model_dump())
    db.add(addition)
    db.flush()
    _recalculate_totals(db, settlement)
    db.refresh(addition)
    return addition, None


def update_addition(
    db: Session,
    addition_id: int,
    payload: SettlementAdditionUpdate,
) -> Optional[SettlementAddition]:
    addition = db.query(SettlementAddition).filter(
        SettlementAddition.id == addition_id
    ).first()
    if not addition:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(addition, key, value)
    db.flush()
    _recalculate_totals(db, addition.settlement)
    db.refresh(addition)
    return addition


def delete_addition(db: Session, addition_id: int) -> bool:
    addition = db.query(SettlementAddition).filter(
        SettlementAddition.id == addition_id
    ).first()
    if not addition:
        return False
    settlement = addition.settlement
    db.delete(addition)
    db.flush()
    _recalculate_totals(db, settlement)
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  Deductions
# ══════════════════════════════════════════════════════════════════════════════

def get_deductions(db: Session, settlement_id: int) -> List[SettlementDeduction]:
    return (
        db.query(SettlementDeduction)
        .filter(SettlementDeduction.settlement_id == settlement_id)
        .order_by(SettlementDeduction.id.asc())
        .all()
    )


def add_deduction(
    db: Session,
    settlement_id: int,
    payload: SettlementDeductionCreate,
) -> tuple:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None, "Settlement not found"

    deduction = SettlementDeduction(settlement_id=settlement_id, **payload.model_dump())
    db.add(deduction)
    db.flush()
    _recalculate_totals(db, settlement)
    db.refresh(deduction)
    return deduction, None


def update_deduction(
    db: Session,
    deduction_id: int,
    payload: SettlementDeductionUpdate,
) -> Optional[SettlementDeduction]:
    deduction = db.query(SettlementDeduction).filter(
        SettlementDeduction.id == deduction_id
    ).first()
    if not deduction:
        return None
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(deduction, key, value)
    db.flush()
    _recalculate_totals(db, deduction.settlement)
    db.refresh(deduction)
    return deduction


def delete_deduction(db: Session, deduction_id: int) -> bool:
    deduction = db.query(SettlementDeduction).filter(
        SettlementDeduction.id == deduction_id
    ).first()
    if not deduction:
        return False
    settlement = deduction.settlement
    db.delete(deduction)
    db.flush()
    _recalculate_totals(db, settlement)
    return True


# ══════════════════════════════════════════════════════════════════════════════
#  Dashboard (4 cards on UI)
# ══════════════════════════════════════════════════════════════════════════════

def get_dashboard(db: Session, settlement_id: int) -> dict:
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None
    return {
        "current_settlement": settlement.current_settlement,
        "total_additions"   : settlement.total_additions,
        "total_deductions"  : settlement.total_deductions,
        "approval_status"   : settlement.status,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Generate Report (Generate Report button on UI)
# ══════════════════════════════════════════════════════════════════════════════

def generate_report(db: Session, settlement_id: int):
    settlement = _get_by_id(db, settlement_id)
    if not settlement:
        return None, "Settlement not found"
    return settlement, None