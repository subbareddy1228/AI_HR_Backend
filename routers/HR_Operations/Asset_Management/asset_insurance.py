# app/api/v1/asset_insurance.py

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List

from core.database import SessionLocal
from schema.HR_Operations.Asset_Management.asset_insurance import (
    AssetInsuranceCreate,
    AssetInsuranceResponse,
)
from services.asset_insurance_service import create_insurance
from model.HR_Operations.Asset_Management.asset_insurance import AssetInsurance

router = APIRouter(prefix="/asset-insurances", tags=["Asset Insurance"])


# ======================================================
# DB Dependency
# ======================================================
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ======================================================
# CREATE POLICY
# ======================================================
@router.post("/", response_model=AssetInsuranceResponse)
def add_policy(payload: AssetInsuranceCreate, db: Session = Depends(get_db)):
    return create_insurance(db, payload)


# ======================================================
# GET ALL POLICIES
# ======================================================
@router.get("/", response_model=List[AssetInsuranceResponse])
def get_policies(db: Session = Depends(get_db)):
    policies = db.query(AssetInsurance).all()
    return policies


# ======================================================
# GET POLICY BY ID
# ======================================================
@router.get("/{policy_id}", response_model=AssetInsuranceResponse)
def get_policy_by_id(policy_id: int, db: Session = Depends(get_db)):

    policy = db.query(AssetInsurance).filter(
        AssetInsurance.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    return policy


# ======================================================
# DELETE POLICY
# ======================================================
@router.delete("/{policy_id}")
def delete_policy(policy_id: int, db: Session = Depends(get_db)):

    policy = db.query(AssetInsurance).filter(
        AssetInsurance.id == policy_id
    ).first()

    if not policy:
        raise HTTPException(status_code=404, detail="Policy not found")

    db.delete(policy)
    db.commit()

    return {"message": "Policy deleted successfully"}
