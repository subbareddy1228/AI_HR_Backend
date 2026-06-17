
import io
import csv
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from schema.Payroll.reimbursement import (
    ClaimApprovalLogResponse,
    ClaimListItem,
    FinanceApprovalRequest,
    ManagerApprovalRequest,
    MarkPaidRequest,
    ReimbursementBalanceResponse,
    ReimbursementClaimCreate,
    ReimbursementClaimResponse,
    ReimbursementDashboard,
    ReimbursementReports,
    ReimbursementTypeCreate,
    ReimbursementTypeResponse,
    ReimbursementTypeUpdate,
)
from services.Payroll.reimbursement_service import (
    create_type, deactivate_type, get_type, list_types, update_type,
    finance_approve, finance_reject, get_claim, list_claims, manager_approve,
    manager_reject, mark_paid, submit_claim, export_claims,
    list_balances,
    get_dashboard, get_reports,
)

router = APIRouter(prefix="/reimbursements", tags=["Reimbursements"])


@router.get(
    "/dashboard",
    response_model=ReimbursementDashboard,
    summary="KPI cards — Total Claims | Approved | Pending | Tax Amount",
)
def dashboard(db: Session = Depends(get_db)):
    return get_dashboard(db)


@router.get(
    "/types",
    response_model=List[ReimbursementTypeResponse],
    summary="List reimbursement types (Master tab table)",
)
def list_types_endpoint(
    active_only: bool           = Query(True,  description="Filter inactive types"),
    category:    Optional[str]  = Query(None,  description="HEALTH|TRAVEL|…"),
    db: Session = Depends(get_db),
):
    return list_types(db, active_only=active_only, category=category)


@router.post(
    "/types",
    response_model=ReimbursementTypeResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add new reimbursement type  (+Add Type button → Save)",
)
def create_type_endpoint(
    payload: ReimbursementTypeCreate,
    db: Session = Depends(get_db),
):
    return create_type(db, payload)


@router.get(
    "/types/{type_id}",
    response_model=ReimbursementTypeResponse,
    summary="Get a single reimbursement type",
)
def get_type_endpoint(type_id: int, db: Session = Depends(get_db)):
    return get_type(db, type_id)


@router.patch(
    "/types/{type_id}",
    response_model=ReimbursementTypeResponse,
    summary="Edit reimbursement type  (Edit button → Save)",
)
def update_type_endpoint(
    type_id: int,
    payload: ReimbursementTypeUpdate,
    db: Session = Depends(get_db),
):
    return update_type(db, type_id, payload)


@router.delete(
    "/types/{type_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Deactivate a reimbursement type (soft-delete)",
)
def deactivate_type_endpoint(type_id: int, db: Session = Depends(get_db)):
    deactivate_type(db, type_id)


@router.get(
    "/claims",
    response_model=List[ClaimListItem],
    summary="List claims — Claims tab table (search / status filter / type filter)",
)
def list_claims_endpoint(
    employee_id:   Optional[int]      = Query(None),
    type_id:       Optional[int]      = Query(None),
    claim_status:  Optional[str]      = Query(None, alias="status",
                                              description="PENDING|FINANCE_REVIEW|APPROVED|REJECTED|PAID"),
    date_from:     Optional[datetime] = Query(None),
    date_to:       Optional[datetime] = Query(None),
    search:        Optional[str]      = Query(None,
                                              description="Search by employee name, code or type"),
    skip:  int = Query(0,   ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    return list_claims(
        db, employee_id=employee_id, type_id=type_id,
        claim_status=claim_status, date_from=date_from,
        date_to=date_to, search=search, skip=skip, limit=limit,
    )


@router.post(
    "/claims",
    response_model=ReimbursementClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit new claim  (New Claim modal → Submit Claim button)",
)
def submit_claim_endpoint(
    payload: ReimbursementClaimCreate,
    db: Session = Depends(get_db),
):
    return submit_claim(db, payload)


@router.get(
    "/claims/export",
    summary="Export claims as CSV  (Export button → Export as CSV)",
)
def export_claims_endpoint(
    employee_id:  Optional[int]      = Query(None),
    type_id:      Optional[int]      = Query(None),
    claim_status: Optional[str]      = Query(None, alias="status"),
    date_from:    Optional[datetime] = Query(None),
    date_to:      Optional[datetime] = Query(None),
    search:       Optional[str]      = Query(None),
    db: Session = Depends(get_db),
):
    rows = export_claims(
        db, employee_id=employee_id, type_id=type_id,
        claim_status=claim_status, date_from=date_from,
        date_to=date_to, search=search,
    )

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Employee", "Employee ID", "Type", "Amount", "Tax",
        "Net Amount", "Date", "Status", "Manager Approval",
        "Finance Approval", "Payroll Status", "Description",
    ])
    for r in rows:
        writer.writerow([
            r.id, r.employee, r.employee_id, r.type,
            r.amount, r.tax_amount, r.net_amount, r.date,
            r.status, r.manager_status, r.finance_status,
            r.payroll_status, r.description or "",
        ])

    output.seek(0)
    filename = f"claims-export-{datetime.utcnow().strftime('%Y-%m-%d')}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )


@router.get(
    "/claims/{claim_id}",
    response_model=ReimbursementClaimResponse,
    summary="Full claim detail — View Details modal",
)
def get_claim_endpoint(claim_id: int, db: Session = Depends(get_db)):
    return get_claim(db, claim_id)


@router.get(
    "/claims/{claim_id}/logs",
    response_model=List[ClaimApprovalLogResponse],
    summary="Approval audit trail for a claim",
)
def get_claim_logs(claim_id: int, db: Session = Depends(get_db)):
    claim = get_claim(db, claim_id)
    return claim.logs

@router.patch(
    "/claims/{claim_id}/manager-approve",
    response_model=ReimbursementClaimResponse,
    summary="Manager Approve  (green Approve button when status=PENDING)",
)
def manager_approve_endpoint(
    claim_id: int,
    payload:  ManagerApprovalRequest,
    db: Session = Depends(get_db),
):
    return manager_approve(db, claim_id, payload)


@router.patch(
    "/claims/{claim_id}/manager-reject",
    response_model=ReimbursementClaimResponse,
    summary="Manager Reject  (red Reject button when status=PENDING)",
)
def manager_reject_endpoint(
    claim_id: int,
    payload:  ManagerApprovalRequest,
    db: Session = Depends(get_db),
):
    return manager_reject(db, claim_id, payload)


@router.patch(
    "/claims/{claim_id}/finance-approve",
    response_model=ReimbursementClaimResponse,
    summary="Finance Approve  (green Approve button when status=FINANCE_REVIEW)",
)
def finance_approve_endpoint(
    claim_id: int,
    payload:  FinanceApprovalRequest,
    db: Session = Depends(get_db),
):
    return finance_approve(db, claim_id, payload)


@router.patch(
    "/claims/{claim_id}/finance-reject",
    response_model=ReimbursementClaimResponse,
    summary="Finance Reject  (red Reject button when status=FINANCE_REVIEW)",
)
def finance_reject_endpoint(
    claim_id: int,
    payload:  FinanceApprovalRequest,
    db: Session = Depends(get_db),
):
    return finance_reject(db, claim_id, payload)


@router.patch(
    "/claims/{claim_id}/mark-paid",
    response_model=ReimbursementClaimResponse,
    summary="Mark claim as PAID after payroll processing",
)
def mark_paid_endpoint(
    claim_id: int,
    payload:  MarkPaidRequest,
    db: Session = Depends(get_db),
):
    return mark_paid(db, claim_id, payload)


@router.get(
    "/receipts/{claim_id}",
    summary="Download receipt file — View Details modal → Download button",
)
def download_receipt(claim_id: int, db: Session = Depends(get_db)):

    import os
    claim = get_claim(db, claim_id)

    if not claim.receipt_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No receipt file attached to this claim.",
        )

    if not os.path.exists(claim.receipt_path):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Receipt file not found on server.",
        )

    filename = claim.receipt_filename or os.path.basename(claim.receipt_path)

    def iterfile():
        with open(claim.receipt_path, "rb") as f:
            yield from f

    # Infer media type from extension
    ext = os.path.splitext(filename)[1].lower()
    media_type = {
        ".pdf":  "application/pdf",
        ".jpg":  "image/jpeg",
        ".jpeg": "image/jpeg",
        ".png":  "image/png",
    }.get(ext, "application/octet-stream")

    return StreamingResponse(
        iterfile(),
        media_type=media_type,
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )



@router.get(
    "/balances",
    response_model=List[ReimbursementBalanceResponse],
    summary="Employee Reimbursement Balances — Balances tab",
)
def list_balances_endpoint(
    employee_id: Optional[int] = Query(None),
    type_id:     Optional[int] = Query(None),
    period:      Optional[str] = Query(None, description="e.g. '2024' or '2024-04'"),
    db: Session = Depends(get_db),
):
    return list_balances(db, employee_id=employee_id,
                         type_id=type_id, period=period)


@router.get(
    "/balances/employee/{employee_id}",
    response_model=List[ReimbursementBalanceResponse],
    summary="All balances for a single employee (grouped view)",
)
def employee_balances(employee_id: int, db: Session = Depends(get_db)):
    return list_balances(db, employee_id=employee_id)


@router.get(
    "/reports",
    response_model=ReimbursementReports,
    summary="Reports & Analytics — Claims by Type + Tax Analysis + Monthly Trend + Top Employees",
)
def reports_endpoint(db: Session = Depends(get_db)):
    return get_reports(db)