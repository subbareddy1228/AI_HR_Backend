from __future__ import annotations

import math
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import List, Optional

from fastapi import HTTPException, status
from sqlalchemy import func, case, text
from sqlalchemy.orm import Session

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_allocation import AssetAllocation
from model.HR_Operations.Asset_Management.asset_insurance import AssetInsurance
from model.HR_Operations.Asset_Management.asset_maintenance import AssetMaintenance
from model.HR_Operations.Asset_Management.asset_return import AssetReturn
from schema.HR_Operations.Asset_Management.asset import (
    AssetCreate,
    AssetDashboardStats,
    AssetReportRow,
    AssetUpdate,
    DepreciationScheduleItem,
)



def _compute_depreciation(asset: Asset) -> dict:
    
    today         = date.today()
    purchase_date = asset.purchase_date
    price         = Decimal(str(asset.purchase_price))
    rate          = Decimal(str(asset.depreciation_rate)) / Decimal("100")

    years_held = (today - purchase_date).days / 365.25

    if asset.depreciation_method == "Straight Line":
        useful_life = asset.useful_life_years or 1
        yearly      = (price * rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        accumulated = min(price, (yearly * Decimal(str(years_held))).quantize(Decimal("0.01"), ROUND_HALF_UP))
        current_val = max(Decimal("0"), price - accumulated)

        
        next_calc = date(today.year + 1, purchase_date.month, purchase_date.day)
        if next_calc <= today:
            next_calc = date(today.year + 1, purchase_date.month, purchase_date.day)

    else:
       
        yearly      = (price * rate).quantize(Decimal("0.01"), ROUND_HALF_UP)
        factor      = (Decimal("1") - rate) ** Decimal(str(math.floor(years_held)))
        current_val = (price * factor).quantize(Decimal("0.01"), ROUND_HALF_UP)
        accumulated = (price - current_val).quantize(Decimal("0.01"), ROUND_HALF_UP)
        next_calc   = date(today.year + 1, purchase_date.month, purchase_date.day)

    return {
        "current_value":         current_val,
        "yearly_depreciation":   yearly,
        "accumulated":           accumulated,
        "net_book_value":        current_val,
        "next_calculation_date": next_calc,
    }




def create_asset(db: Session, payload: AssetCreate) -> Asset:
   
    if db.query(Asset).filter(Asset.serial_number == payload.serial_number).first():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Asset with serial number '{payload.serial_number}' already exists.",
        )
    asset = Asset(**payload.model_dump())
    db.add(asset)
    db.commit()
    db.refresh(asset)
    return asset


def get_asset(db: Session, asset_id: int) -> Asset:
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Asset not found.")
    return asset


def list_assets(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
    category: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
) -> List[Asset]:
    q = db.query(Asset)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            Asset.asset_name.ilike(pattern)
            | Asset.serial_number.ilike(pattern)
            | Asset.make.ilike(pattern)
            | Asset.model.ilike(pattern)
        )
    if category:
        q = q.filter(Asset.category == category)
    if status:
        q = q.filter(Asset.status == status)
    if department:
        q = q.filter(Asset.department == department)
    return q.order_by(Asset.asset_name).offset(skip).limit(limit).all()


def update_asset(db: Session, asset_id: int, payload: AssetUpdate) -> Asset:
    asset = get_asset(db, asset_id)
    data  = payload.model_dump(exclude_unset=True)
    for field, value in data.items():
        setattr(asset, field, value)
    db.commit()
    db.refresh(asset)
    return asset


def delete_asset(db: Session, asset_id: int) -> None:
    asset = get_asset(db, asset_id)
    if asset.status == "ALLOCATED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Cannot delete an asset that is currently allocated. Return it first.",
        )
    db.delete(asset)
    db.commit()




def get_dashboard_stats(db: Session) -> AssetDashboardStats:
    today        = date.today()
    warning_days = 30 

    status_counts = (
        db.query(Asset.status, func.count(Asset.id))
        .group_by(Asset.status)
        .all()
    )
    counts = {s: c for s, c in status_counts}

    total      = sum(counts.values())
    allocated  = counts.get("ALLOCATED", 0)
    available  = counts.get("AVAILABLE", 0)
    under_rep  = counts.get("UNDER_MAINTENANCE", 0)
    retired    = counts.get("RETIRED", 0)

    
    total_value = db.query(func.coalesce(func.sum(Asset.purchase_price), 0)).scalar()

    pending_returns = (
        db.query(func.count(AssetReturn.id))
        .filter(AssetReturn.status == "Pending")
        .scalar()
    )

    upcoming_maint = (
        db.query(func.count(AssetMaintenance.id))
        .filter(
            AssetMaintenance.next_due_date >= today,
            AssetMaintenance.next_due_date <= today + timedelta(days=30),
            AssetMaintenance.status != "Cancelled",
        )
        .scalar()
    )

    expiring_insurance = (
        db.query(func.count(AssetInsurance.id))
        .filter(
            AssetInsurance.status == "Active",
            AssetInsurance.end_date >= today,
            AssetInsurance.end_date <= today + timedelta(days=warning_days),
        )
        .scalar()
    )

    utilization = round((allocated / total * 100) if total > 0 else 0.0, 2)

    return AssetDashboardStats(
        total_assets=total,
        allocated=allocated,
        available=available,
        under_repair=under_rep,
        retired=retired,
        pending_returns=pending_returns,
        upcoming_maintenance=upcoming_maint,
        expiring_insurance=expiring_insurance,
        total_asset_value=Decimal(str(total_value)),
        utilization_rate=utilization,
    )




def get_depreciation_schedule(
    db: Session,
    skip: int = 0,
    limit: int = 50,
    search: Optional[str] = None,
) -> List[DepreciationScheduleItem]:
    q = db.query(Asset).filter(Asset.status != "RETIRED")
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            Asset.asset_name.ilike(pattern) | Asset.serial_number.ilike(pattern)
        )
    assets = q.order_by(Asset.asset_name).offset(skip).limit(limit).all()

    result = []
    for asset in assets:
        dep = _compute_depreciation(asset)
        result.append(
            DepreciationScheduleItem(
                asset_id=asset.id,
                asset_name=asset.asset_name,
                serial_number=asset.serial_number,
                purchase_price=Decimal(str(asset.purchase_price)),
                depreciation_rate=asset.depreciation_rate,
                depreciation_method=asset.depreciation_method,
                useful_life_years=asset.useful_life_years,
                **dep,
            )
        )
    return result




def get_asset_report(
    db: Session,
    category: Optional[str] = None,
    status: Optional[str] = None,
    department: Optional[str] = None,
) -> List[AssetReportRow]:
    
    
    latest_alloc = (
        db.query(
            AssetAllocation.asset_id,
            AssetAllocation.employee_name,
        )
        .filter(AssetAllocation.status == "Active")
        .subquery()
    )

    q = (
        db.query(Asset, latest_alloc.c.employee_name)
        .outerjoin(latest_alloc, Asset.id == latest_alloc.c.asset_id)
    )
    if category:
        q = q.filter(Asset.category == category)
    if status:
        q = q.filter(Asset.status == status)
    if department:
        q = q.filter(Asset.department == department)

    rows = []
    for asset, allocated_to in q.order_by(Asset.asset_name).all():
        dep = _compute_depreciation(asset)
        rows.append(
            AssetReportRow(
                asset_id=asset.id,
                asset_name=asset.asset_name,
                category=asset.category,
                serial_number=asset.serial_number,
                status=asset.status,
                condition=asset.condition,
                department=asset.department,
                location=asset.location,
                purchase_price=Decimal(str(asset.purchase_price)),
                current_value=dep["current_value"],
                allocated_to=allocated_to,
                warranty_until=asset.warranty_until,
            )
        )
    return rows
