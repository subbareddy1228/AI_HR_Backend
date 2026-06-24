"""
routers/HR_Operations/Asset_Management/asset_dashboard.py

Aggregation endpoints sitting on top of the existing Asset Management
sub-modules (assets, allocations, returns, maintenance, insurance):

  Dashboard       : Quick Statistics tiles + Asset Status Overview
  Depreciation    : straight-line calculator, single asset + schedule for all
  Reports         : 6 individual PDF reports + bulk "Generate All Reports"
"""

import io
import zipfile
from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from model.HR_Operations.Asset_Management.asset import Asset
from schema.HR_Operations.Asset_Management.asset_dashboard import (
    AssetDashboardStats,
    AssetStatusOverview,
    DepreciationResult,
    BulkReportRequest,
)
from services.asset_dashboard_service import (
    get_dashboard_stats,
    get_asset_status_overview,
    calculate_depreciation,
    calculate_depreciation_for_all,
    generate_asset_inventory_report,
    generate_employee_allocation_report,
    generate_depreciation_report,
    generate_maintenance_report,
    generate_insurance_report,
    generate_asset_return_report,
)

router = APIRouter(prefix="/assets", tags=["Asset Management Dashboard"])


# ======================================================
# 1. DASHBOARD
# ======================================================
@router.get("/dashboard/stats", response_model=AssetDashboardStats)
def get_dashboard(db: Session = Depends(get_db)):
    """Powers the Quick Statistics tiles: Total Asset Value, Utilization %, etc."""
    return get_dashboard_stats(db)


@router.get("/dashboard/status-overview", response_model=AssetStatusOverview)
def get_status_overview(db: Session = Depends(get_db)):
    """Powers the 'Asset Status Overview' + category distribution panel."""
    return get_asset_status_overview(db)


# ======================================================
# 2. DEPRECIATION
# ======================================================
# NOTE: literal-path routes (below) are registered BEFORE the
# "/{asset_id}/depreciation" pattern further down. FastAPI matches routes
# in registration order, and "/assets/depreciation/schedule" or
# "/assets/reports/inventory" would otherwise be incorrectly captured by
# "/{asset_id}/depreciation" (since "depreciation"/"reports" would be
# parsed as the asset_id path param first, and only fail with a 422 instead
# of falling through to the correct route).
@router.get("/depreciation/schedule", response_model=List[DepreciationResult])
def get_depreciation_schedule(
    as_of: Optional[date] = Query(None),
    db: Session = Depends(get_db),
):
    """Powers the 'Asset Depreciation Schedule' table on the Depreciation tab."""
    return calculate_depreciation_for_all(db, as_of)


# ======================================================
# 3. REPORTS  (6 individual PDF reports) -- also literal paths, must
# come before "/{asset_id}/depreciation" for the same reason as above.
# ======================================================
_REPORT_GENERATORS = {
    "inventory": (generate_asset_inventory_report, "asset_inventory_report.pdf"),
    "allocation": (generate_employee_allocation_report, "employee_allocation_report.pdf"),
    "depreciation": (generate_depreciation_report, "depreciation_report.pdf"),
    "maintenance": (generate_maintenance_report, "maintenance_report.pdf"),
    "insurance": (generate_insurance_report, "insurance_report.pdf"),
    "returns": (generate_asset_return_report, "asset_return_report.pdf"),
}


@router.get("/reports/{report_type}")
def download_report(report_type: str, db: Session = Depends(get_db)):
    """
    report_type one of: inventory | allocation | depreciation | maintenance | insurance | returns
    Matches the 6 "Download PDF Report" buttons in the Reports tab.
    """
    entry = _REPORT_GENERATORS.get(report_type)
    if not entry:
        raise HTTPException(
            status_code=400,
            detail=f"report_type must be one of {list(_REPORT_GENERATORS.keys())}",
        )

    generator, filename = entry
    buffer = generator(db)

    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/reports/bulk-generate")
def bulk_generate_reports(payload: BulkReportRequest, db: Session = Depends(get_db)):
    """
    Powers the 'Bulk Report Generator' -> 'Generate All Reports' button.
    Returns a single ZIP containing all requested PDF reports.

    Note: the date range (from_date/to_date) is accepted for API
    compatibility with the frontend's date pickers; the current report
    generators always export the full dataset rather than filtering by
    date, since none of the 5 underlying tables expose a single date field
    that unambiguously matches "report period" across all 6 report types.
    """
    report_types = payload.report_types or list(_REPORT_GENERATORS.keys())

    invalid = [r for r in report_types if r not in _REPORT_GENERATORS]
    if invalid:
        raise HTTPException(status_code=400, detail=f"Invalid report types: {invalid}")

    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for report_type in report_types:
            generator, filename = _REPORT_GENERATORS[report_type]
            pdf_buffer = generator(db)
            zf.writestr(filename, pdf_buffer.read())

    zip_buffer.seek(0)
    return StreamingResponse(
        zip_buffer,
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="asset_reports_bundle.zip"'},
    )


# ======================================================
# Catch-all "/{asset_id}/depreciation" -- MUST be registered last among
# GET routes under /assets/, since {asset_id} would otherwise swallow any
# literal path above it (e.g. "depreciation", "reports") that hasn't been
# registered yet at the time this route is added.
# ======================================================
@router.get("/{asset_id}/depreciation", response_model=DepreciationResult)
def get_asset_depreciation(
    asset_id: int,
    as_of: Optional[date] = Query(None, description="Calculate as of this date, defaults to today"),
    db: Session = Depends(get_db),
):
    asset = db.query(Asset).filter(Asset.id == asset_id).first()
    if not asset:
        raise HTTPException(status_code=404, detail="Asset not found")

    return calculate_depreciation(asset, as_of)