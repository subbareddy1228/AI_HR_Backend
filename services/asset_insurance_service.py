from __future__ import annotations

from datetime import date, timedelta
from decimal import Decimal
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_insurance import AssetInsurance
from schema.HR_Operations.Asset_Management.asset_insurance import (
    AssetInsuranceCreate,
    AssetInsuranceUpdate,
)


def create_insurance(db: Session, payload: AssetInsuranceCreate) -> AssetInsurance:
   
    asset = db.query(Asset).filter(Asset.id == payload.asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")

    
    if db.query(AssetInsurance).filter(AssetInsurance.policy_number == payload.policy_number).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Policy number '{payload.policy_number}' already exists.",
        )

    insurance = AssetInsurance(**payload.model_dump())
    db.add(insurance)
    db.commit()
    db.refresh(insurance)
    return insurance


def get_insurance(db: Session, insurance_id: int) -> AssetInsurance:
    ins = db.query(AssetInsurance).filter(AssetInsurance.id == insurance_id).first()
    if not ins:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Insurance policy not found.")
    return ins


def list_insurances(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    ins_status: Optional[str] = None,
    asset_id: Optional[int] = None,
) -> List[AssetInsurance]:
    q = db.query(AssetInsurance)
    if asset_id:
        q = q.filter(AssetInsurance.asset_id == asset_id)
    if ins_status:
        q = q.filter(AssetInsurance.status == ins_status)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            AssetInsurance.insurance_provider.ilike(pattern)
            | AssetInsurance.policy_number.ilike(pattern)
        )
    return q.order_by(AssetInsurance.end_date).offset(skip).limit(limit).all()


def update_insurance(
    db: Session, insurance_id: int, payload: AssetInsuranceUpdate
) -> AssetInsurance:
    ins  = get_insurance(db, insurance_id)
    data = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(ins, field, value)
    db.commit()
    db.refresh(ins)
    return ins


def file_claim(
    db: Session,
    insurance_id: int,
    claim_amount: Decimal,
    claim_notes: str,
) -> AssetInsurance:
    
    ins = get_insurance(db, insurance_id)
    if ins.status not in ("Active",):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Cannot file a claim on a policy with status '{ins.status}'.",
        )
    ins.claims_count  += 1
    ins.claims_amount  = (ins.claims_amount or Decimal("0")) + claim_amount
    ins.claims_notes   = (ins.claims_notes or "") + f"\n[CLAIM {ins.claims_count}] {claim_notes}"
    ins.status         = "Claim Filed"
    db.commit()
    db.refresh(ins)
    return ins


def list_expiring_policies(
    db: Session,
    days_ahead: int = 30,
) -> List[AssetInsurance]:
    
    today = date.today()
    return (
        db.query(AssetInsurance)
        .filter(
            AssetInsurance.status == "Active",
            AssetInsurance.end_date >= today,
            AssetInsurance.end_date <= today + timedelta(days=days_ahead),
        )
        .order_by(AssetInsurance.end_date)
        .all()
    )


def sync_expired_policies(db: Session) -> int:
   
    today   = date.today()
    expired = (
        db.query(AssetInsurance)
        .filter(
            AssetInsurance.status == "Active",
            AssetInsurance.end_date < today,
        )
        .all()
    )
    for ins in expired:
        ins.status = "Expired"
    db.commit()
    return len(expired)
