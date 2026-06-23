
from typing import Optional

from fastapi import APIRouter, Depends, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.dependencies import get_db
from schema.Payroll.final_settlement import (
    ApprovalPayload,
    AssetCreate,
    AssetUpdate,
    BonusUpdate,
    DeductionUpdate,
    FinalSettlementCreate,
    FinalSettlementListItem,
    FinalSettlementResponse,
    FinalSettlementUpdate,
    GratuityUpdate,
    LeaveEncashmentUpdate,
    NoticePeriodUpdate,
    PaginatedSettlementList,
    PaymentProcessPayload,
    PaymentUpdate,
    RejectionPayload,
    SalaryBreakdownUpdate,
    SettlementStatsResponse,
)
from services.Payroll.final_settlement_service import (
    add_asset,
    approve_settlement,
    cancel_settlement,
    create_settlement,
    delete_asset,
    delete_settlement,
    export_settlement_csv,
    export_settlement_report_csv,
    generate_document,
    get_settlement,
    get_settlement_by_employee,
    get_settlement_stats,
    issue_document,
    list_settlements,
    process_payment,
    recalculate_settlement,
    reject_settlement,
    submit_for_approval,
    update_asset,
    update_bonus,
    update_deductions,
    update_gratuity,
    update_leave_encashment,
    update_notice_period,
    update_payment_info,
    update_salary_breakdown,
    update_settlement,
)

router = APIRouter(
    prefix="/final-settlements",
    tags=["Final Settlement"],
)


@router.get(
    "/stats",
    response_model=SettlementStatsResponse,
    summary="Settlement KPI cards",
    description=(
        "Returns the four top-card values shown on the UI: Current Settlement, "
        "Total Additions, Total Deductions, and Approval Status, plus aggregate "
        "counts for Pending / Approved / Paid / Cancelled."
    ),
)
def settlement_stats(
    settlement_id: Optional[int] = Query(None, description="Focus on a specific settlement"),
    db: Session = Depends(get_db),
):
    return get_settlement_stats(db, settlement_id)


@router.get(
    "/export/report",
    summary="Export all settlements (CSV)",
    description="Download a CSV with one row per settlement — useful for payroll audit.",
)
def export_all_settlements(db: Session = Depends(get_db)):
    data = export_settlement_report_csv(db)
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=final_settlements_report.csv"},
    )


@router.get(
    "",
    response_model=PaginatedSettlementList,
    summary="List all settlements (paginated)",
)
def list_all_settlements(
    status_filter: Optional[str] = Query(None, alias="status", description="Draft | Pending Approval | Approved | Paid | Cancelled"),
    exit_type: Optional[str]     = Query(None, description="Resignation | Termination | Retirement | Absconding | Contract End"),
    search: Optional[str]        = Query(None, description="Search by employee name, code, or settlement code"),
    page: int                    = Query(1, ge=1),
    page_size: int               = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    total, items = list_settlements(db, status_filter, exit_type, search, page, page_size)
    return PaginatedSettlementList(total=total, page=page, page_size=page_size, items=items)


@router.post(
    "",
    response_model=FinalSettlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initiate a new final settlement",
    description=(
        "Creates a settlement in Draft status. Automatically seeds:\n"
        "- Default sub-blocks (notice period, salary, leave, bonus, gratuity, deductions, payment)\n"
        "- 4-step timeline (Notice Initiated → Document Collection → Calculation → Payment)\n"
        "- 5-item document checklist (Form16, Form19, Form10C, Experience Letter, Relieving Letter)\n\n"
        "Raises 409 if a settlement already exists for the employee."
    ),
)
def create_new_settlement(payload: FinalSettlementCreate, db: Session = Depends(get_db)):
    return create_settlement(db, payload)


@router.get(
    "/employee/{employee_id}",
    response_model=FinalSettlementResponse,
    summary="Get settlement by employee ID",
)
def get_by_employee(employee_id: int, db: Session = Depends(get_db)):
    return get_settlement_by_employee(db, employee_id)


@router.get(
    "/{settlement_id}",
    response_model=FinalSettlementResponse,
    summary="Full settlement detail (all nested blocks)",
)
def get_settlement_detail(settlement_id: int, db: Session = Depends(get_db)):
    return get_settlement(db, settlement_id)


@router.put(
    "/{settlement_id}",
    response_model=FinalSettlementResponse,
    summary="Update settlement header fields",
    description="Editable only in Draft or Pending Approval status.",
)
def update_settlement_header(
    settlement_id: int,
    payload: FinalSettlementUpdate,
    db: Session = Depends(get_db),
):
    return update_settlement(db, settlement_id, payload)


@router.delete(
    "/{settlement_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete settlement",
    description="Cannot delete a Paid settlement.",
)
def delete_settlement_record(settlement_id: int, db: Session = Depends(get_db)):
    delete_settlement(db, settlement_id)


@router.post(
    "/{settlement_id}/recalculate",
    response_model=FinalSettlementResponse,
    summary="Recalculate all settlement components",
    description=(
        "Re-runs the full computation engine:\n"
        "1. Salary for days worked (gross / working_days × days_served)\n"
        "2. Notice period shortfall recovery (daily_rate × shortfall_days)\n"
        "3. Leave encashment (earned_leave_balance × encashment_rate)\n"
        "4. Pro-rata bonus ((annual_bonus / 365) × pro_rata_days)\n"
        "5. Gratuity ((basic / 26) × 15 × completed_years  if ≥ 5 years)\n"
        "6. Asset penalties (Lost / Damaged / Pending matrices)\n"
        "7. Updates header totals (total_additions, total_deductions, net_settlement)\n\n"
        "Disabled for Paid settlements."
    ),
)
def recalculate(settlement_id: int, db: Session = Depends(get_db)):
    return recalculate_settlement(db, settlement_id)


@router.post(
    "/{settlement_id}/submit",
    response_model=FinalSettlementResponse,
    summary="Submit for approval (Draft → Pending Approval)",
)
def submit_settlement(
    settlement_id: int,
    submitted_by_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return submit_for_approval(db, settlement_id, submitted_by_name)


@router.post(
    "/{settlement_id}/approve",
    response_model=FinalSettlementResponse,
    summary="Approve settlement (Pending Approval → Approved)",
    description="Triggers the 'Approve' button in Quick Actions.",
)
def approve(
    settlement_id: int,
    payload: ApprovalPayload,
    db: Session = Depends(get_db),
):
    return approve_settlement(db, settlement_id, payload)


@router.post(
    "/{settlement_id}/reject",
    response_model=FinalSettlementResponse,
    summary="Reject settlement (→ back to Draft)",
)
def reject(
    settlement_id: int,
    payload: RejectionPayload,
    db: Session = Depends(get_db),
):
    return reject_settlement(db, settlement_id, payload)


@router.post(
    "/{settlement_id}/pay",
    response_model=FinalSettlementResponse,
    summary="Process payment (Approved → Paid)",
    description=(
        "Marks settlement as Paid, updates the payment sub-block with UTR/reference "
        "number and marks the Payment Processing timeline milestone as completed."
    ),
)
def pay(
    settlement_id: int,
    payload: PaymentProcessPayload,
    db: Session = Depends(get_db),
):
    return process_payment(db, settlement_id, payload)


@router.post(
    "/{settlement_id}/cancel",
    response_model=FinalSettlementResponse,
    summary="Cancel settlement",
)
def cancel(
    settlement_id: int,
    reason: str = Query(..., description="Cancellation reason"),
    cancelled_by_name: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return cancel_settlement(db, settlement_id, reason, cancelled_by_name)

@router.patch(
    "/{settlement_id}/notice-period",
    response_model=FinalSettlementResponse,
    summary="Update notice period block",
    description=(
        "Updates notice period details and automatically triggers a recalculate "
        "so notice_period_recovery reflects the latest shortfall."
    ),
)
def patch_notice_period(
    settlement_id: int,
    payload: NoticePeriodUpdate,
    db: Session = Depends(get_db),
):
    return update_notice_period(db, settlement_id, payload)


@router.patch(
    "/{settlement_id}/salary-breakdown",
    response_model=FinalSettlementResponse,
    summary="Update salary breakdown block",
    description="Updates gross components and days worked, then recalculates totals.",
)
def patch_salary_breakdown(
    settlement_id: int,
    payload: SalaryBreakdownUpdate,
    db: Session = Depends(get_db),
):
    return update_salary_breakdown(db, settlement_id, payload)


@router.patch(
    "/{settlement_id}/leave-encashment",
    response_model=FinalSettlementResponse,
    summary="Update leave encashment block",
)
def patch_leave_encashment(
    settlement_id: int,
    payload: LeaveEncashmentUpdate,
    db: Session = Depends(get_db),
):
    return update_leave_encashment(db, settlement_id, payload)


@router.patch(
    "/{settlement_id}/bonus",
    response_model=FinalSettlementResponse,
    summary="Update bonus block",
)
def patch_bonus(
    settlement_id: int,
    payload: BonusUpdate,
    db: Session = Depends(get_db),
):
    return update_bonus(db, settlement_id, payload)


@router.patch(
    "/{settlement_id}/gratuity",
    response_model=FinalSettlementResponse,
    summary="Update gratuity block",
    description=(
        "Gratuity is auto-computed: (basic / 26) × 15 × completed_full_years. "
        "Employee must have ≥ eligibility_years (default 5) of service to qualify."
    ),
)
def patch_gratuity(
    settlement_id: int,
    payload: GratuityUpdate,
    db: Session = Depends(get_db),
):
    return update_gratuity(db, settlement_id, payload)


@router.patch(
    "/{settlement_id}/deductions",
    response_model=FinalSettlementResponse,
    summary="Update deductions block",
    description=(
        "Update loan, advance, TDS, and other manual deductions. "
        "notice_period_recovery and asset_penalty are computed automatically — "
        "do not pass them manually."
    ),
)
def patch_deductions(
    settlement_id: int,
    payload: DeductionUpdate,
    db: Session = Depends(get_db),
):
    return update_deductions(db, settlement_id, payload)

@router.post(
    "/{settlement_id}/assets",
    response_model=FinalSettlementResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add asset to return checklist",
)
def add_asset_to_settlement(
    settlement_id: int,
    payload: AssetCreate,
    db: Session = Depends(get_db),
):
    return add_asset(db, settlement_id, payload)


@router.patch(
    "/{settlement_id}/assets/{asset_id}",
    response_model=FinalSettlementResponse,
    summary="Update asset return status / condition",
    description=(
        "Set return_status to 'returned', 'lost', or 'damaged'. "
        "Asset penalty is auto-recomputed after update."
    ),
)
def update_asset_record(
    settlement_id: int,
    asset_id: int,
    payload: AssetUpdate,
    db: Session = Depends(get_db),
):
    return update_asset(db, settlement_id, asset_id, payload)


@router.delete(
    "/{settlement_id}/assets/{asset_id}",
    response_model=FinalSettlementResponse,
    summary="Remove asset from checklist",
)
def remove_asset(
    settlement_id: int,
    asset_id: int,
    db: Session = Depends(get_db),
):
    return delete_asset(db, settlement_id, asset_id)


@router.patch(
    "/{settlement_id}/payment",
    response_model=FinalSettlementResponse,
    summary="Update bank / payment details",
    description=(
        "Updates account number, IFSC, bank name, payment mode. "
        "To mark the settlement as fully paid use POST /{id}/pay instead."
    ),
)
def patch_payment(
    settlement_id: int,
    payload: PaymentUpdate,
    db: Session = Depends(get_db),
):
    return update_payment_info(db, settlement_id, payload)

@router.post(
    "/{settlement_id}/documents/{doc_type}/generate",
    response_model=FinalSettlementResponse,
    summary="Generate a settlement document",
    description=(
        "Marks the document as generated and sets its download_url. "
        "Supported types: Form16, Form19, Form10C, Experience Letter, Relieving Letter. "
        "Once all 5 documents are generated the Document Collection timeline milestone "
        "is automatically marked complete."
    ),
)
def generate_doc(
    settlement_id: int,
    doc_type: str,
    generated_by: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    return generate_document(db, settlement_id, doc_type, generated_by)


@router.post(
    "/{settlement_id}/documents/{doc_type}/issue",
    response_model=FinalSettlementResponse,
    summary="Mark a document as issued to the employee",
)
def issue_doc(
    settlement_id: int,
    doc_type: str,
    db: Session = Depends(get_db),
):
    return issue_document(db, settlement_id, doc_type)


@router.get(
    "/{settlement_id}/export",
    summary="Export single settlement as CSV",
    description=(
        "Downloads a structured CSV of the complete settlement — additions breakdown, "
        "deductions breakdown, and net payable. Useful for the 'Export' Quick Action button."
    ),
)
def export_single(settlement_id: int, db: Session = Depends(get_db)):
    data = export_settlement_csv(db, settlement_id)
    settlement = get_settlement(db, settlement_id)
    filename = f"settlement_{settlement.settlement_code}.csv"
    return StreamingResponse(
        iter([data]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"},
    )
