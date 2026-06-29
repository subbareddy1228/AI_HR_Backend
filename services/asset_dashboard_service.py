"""
services/asset_dashboard_service.py

Aggregation layer for the Asset Management System dashboard, depreciation
calculator, and PDF report generation. The 5 core sub-modules (assets,
allocations, returns, maintenance, insurance) already exist and are not
modified here -- this file only reads from them.
"""

import io
from datetime import date, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from model.HR_Operations.Asset_Management.asset import Asset
from model.HR_Operations.Asset_Management.asset_allocation import AssetAllocation
from model.HR_Operations.Asset_Management.asset_return import AssetReturn
from model.HR_Operations.Asset_Management.asset_maintenance import AssetMaintenance
from model.HR_Operations.Asset_Management.asset_insurance import AssetInsurance


# ======================================================
# DASHBOARD / QUICK STATISTICS
# ======================================================
def get_dashboard_stats(db: Session) -> dict:
    total_assets = db.query(func.count(Asset.id)).scalar() or 0
    total_asset_value = db.query(func.sum(Asset.purchase_price)).scalar() or 0

    allocated_assets = (
        db.query(func.count(Asset.id)).filter(Asset.status == "ALLOCATED").scalar() or 0
    )
    available_assets = (
        db.query(func.count(Asset.id)).filter(Asset.status == "AVAILABLE").scalar() or 0
    )
    under_repair = (
        db.query(func.count(Asset.id)).filter(Asset.status == "UNDER_MAINTENANCE").scalar() or 0
    )

    utilization_rate = round((allocated_assets / total_assets) * 100, 1) if total_assets else 0.0

    today = date.today()
    upcoming_cutoff = today + timedelta(days=30)
    upcoming_maintenance = (
        db.query(func.count(AssetMaintenance.id))
        .filter(
            AssetMaintenance.next_maintenance_date.isnot(None),
            AssetMaintenance.next_maintenance_date >= today,
            AssetMaintenance.next_maintenance_date <= upcoming_cutoff,
        )
        .scalar()
        or 0
    )

    expiring_insurance = (
        db.query(func.count(AssetInsurance.id))
        .filter(AssetInsurance.end_date >= today, AssetInsurance.end_date <= upcoming_cutoff)
        .scalar()
        or 0
    )

    # "pending returns" = allocations still ACTIVE (asset issued, not yet returned),
    # matching the "Pending Returns" tile in the screenshot.
    pending_returns = (
        db.query(func.count(AssetAllocation.id))
        .filter(AssetAllocation.status == "ACTIVE")
        .scalar()
        or 0
    )

    return {
        "total_asset_value": float(total_asset_value),
        "asset_utilization_percent": utilization_rate,
        "upcoming_maintenance": upcoming_maintenance,
        "expiring_insurance": expiring_insurance,
        "total_assets": total_assets,
        "allocated_assets": allocated_assets,
        "available_assets": available_assets,
        "under_repair": under_repair,
        "pending_returns": pending_returns,
    }


def get_asset_status_overview(db: Session) -> dict:
    available = db.query(func.count(Asset.id)).filter(Asset.status == "AVAILABLE").scalar() or 0
    allocated = db.query(func.count(Asset.id)).filter(Asset.status == "ALLOCATED").scalar() or 0
    under_repair = db.query(func.count(Asset.id)).filter(Asset.status == "UNDER_MAINTENANCE").scalar() or 0
    retired = db.query(func.count(Asset.id)).filter(Asset.status == "RETIRED").scalar() or 0

    category_rows = db.query(Asset.category, func.count(Asset.id)).group_by(Asset.category).all()

    return {
        "available": available,
        "allocated": allocated,
        "under_repair": under_repair,
        "retired": retired,
        "category_distribution": [{"category": c, "count": n} for c, n in category_rows],
    }


# ======================================================
# DEPRECIATION CALCULATOR  (straight-line method)
# ======================================================
def calculate_depreciation(asset: Asset, as_of: Optional[date] = None) -> dict:
    """
    Straight-line depreciation:
      yearly_depreciation = purchase_price * (depreciation_rate / 100)
      accumulated = yearly_depreciation * years_elapsed (capped at purchase_price)
      net_book_value = purchase_price - accumulated
      next_calculation = purchase_date + (years_elapsed + 1) years
    """
    as_of = as_of or date.today()
    purchase_price = float(asset.purchase_price)
    rate = asset.depreciation_rate / 100

    yearly_depreciation = round(purchase_price * rate, 2)

    years_elapsed = (as_of - asset.purchase_date).days / 365.25
    full_years_elapsed = int(years_elapsed)

    accumulated = min(round(yearly_depreciation * years_elapsed, 2), purchase_price)
    net_book_value = round(purchase_price - accumulated, 2)
    current_value = max(net_book_value, 0.0)

    next_calc_year = asset.purchase_date.year + full_years_elapsed + 1
    try:
        next_calculation_date = asset.purchase_date.replace(year=next_calc_year)
    except ValueError:
        # handles Feb 29 purchase dates on non-leap next years
        next_calculation_date = asset.purchase_date.replace(year=next_calc_year, day=28)

    return {
        "asset_id": asset.id,
        "purchase_price": purchase_price,
        "depreciation_rate": asset.depreciation_rate,
        "method": "Straight Line",
        "current_value": current_value,
        "yearly_depreciation": yearly_depreciation,
        "accumulated_depreciation": accumulated,
        "net_book_value": net_book_value,
        "next_calculation_date": next_calculation_date,
    }


def calculate_depreciation_for_all(db: Session, as_of: Optional[date] = None) -> list:
    assets = db.query(Asset).filter(Asset.status != "RETIRED").all()
    return [calculate_depreciation(asset, as_of) for asset in assets]


# ======================================================
# REPORTS (PDF) -- matches the 6 report cards + bulk generator
# ======================================================
def _pdf_table(title: str, headers: list, rows: list) -> io.BytesIO:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    elements = [Paragraph(title, styles["Heading2"]), Spacer(1, 10)]

    table_data = [headers] + rows
    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer


def generate_asset_inventory_report(db: Session) -> io.BytesIO:
    assets = db.query(Asset).order_by(Asset.id).all()
    rows = [
        [a.asset_name, a.category, a.serial_number, str(a.purchase_price), a.condition, a.status, a.department]
        for a in assets
    ]
    headers = ["Asset Name", "Category", "Serial No.", "Purchase Price", "Condition", "Status", "Department"]
    return _pdf_table("Asset Inventory Report", headers, rows)


def generate_employee_allocation_report(db: Session) -> io.BytesIO:
    rows_query = (
        db.query(AssetAllocation, Asset)
        .join(Asset, AssetAllocation.asset_id == Asset.id)
        .order_by(AssetAllocation.allocated_at.desc())
        .all()
    )
    rows = [
        [alloc.employee_name, alloc.employee_id, alloc.department, asset.asset_name,
         alloc.allocated_at.strftime("%d-%b-%Y"), alloc.status]
        for alloc, asset in rows_query
    ]
    headers = ["Employee", "Employee ID", "Department", "Asset", "Allocated On", "Status"]
    return _pdf_table("Employee-wise Allocation Report", headers, rows)


def generate_depreciation_report(db: Session) -> io.BytesIO:
    depreciation_data = calculate_depreciation_for_all(db)
    asset_map = {a.id: a for a in db.query(Asset).all()}

    rows = []
    for d in depreciation_data:
        asset = asset_map.get(d["asset_id"])
        rows.append([
            asset.asset_name if asset else "",
            str(d["purchase_price"]),
            f"{d['depreciation_rate']}%",
            str(d["current_value"]),
            str(d["accumulated_depreciation"]),
            str(d["net_book_value"]),
        ])
    headers = ["Asset", "Purchase Price", "Rate", "Current Value", "Accumulated", "Net Book Value"]
    return _pdf_table("Depreciation Report", headers, rows)


def generate_maintenance_report(db: Session) -> io.BytesIO:
    rows_query = (
        db.query(AssetMaintenance, Asset)
        .join(Asset, AssetMaintenance.asset_id == Asset.id)
        .order_by(AssetMaintenance.maintenance_date.desc())
        .all()
    )
    rows = [
        [asset.asset_name, m.maintenance_type, m.maintenance_date.strftime("%d-%b-%Y"),
         str(m.cost), m.performed_by, m.description[:50]]
        for m, asset in rows_query
    ]
    headers = ["Asset", "Type", "Date", "Cost", "Performed By", "Description"]
    return _pdf_table("Maintenance Report", headers, rows)


def generate_insurance_report(db: Session) -> io.BytesIO:
    rows_query = (
        db.query(AssetInsurance, Asset)
        .join(Asset, AssetInsurance.asset_id == Asset.id)
        .order_by(AssetInsurance.end_date)
        .all()
    )
    rows = [
        [asset.asset_name, ins.insurance_provider, ins.policy_number,
         str(ins.coverage_amount), str(ins.premium_amount),
         ins.end_date.strftime("%d-%b-%Y")]
        for ins, asset in rows_query
    ]
    headers = ["Asset", "Provider", "Policy No.", "Coverage", "Premium", "Expiry"]
    return _pdf_table("Insurance Report", headers, rows)


def generate_asset_return_report(db: Session) -> io.BytesIO:
    rows_query = (
        db.query(AssetReturn, AssetAllocation, Asset)
        .join(AssetAllocation, AssetReturn.allocation_id == AssetAllocation.id)
        .join(Asset, AssetAllocation.asset_id == Asset.id)
        .order_by(AssetReturn.returned_at.desc())
        .all()
    )
    rows = [
        [asset.asset_name, alloc.employee_name, ret.return_reason, ret.condition_at_return,
         str(ret.penalty_amount), ret.returned_at.strftime("%d-%b-%Y")]
        for ret, alloc, asset in rows_query
    ]
    headers = ["Asset", "Employee", "Return Reason", "Condition", "Penalty", "Returned On"]
    return _pdf_table("Asset Return Report", headers, rows)