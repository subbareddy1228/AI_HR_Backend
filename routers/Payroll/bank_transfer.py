
from __future__ import annotations

import io
import logging
from datetime import datetime
from typing import List, Optional

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Response,
    status,
)
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from core.database import get_db
from model.Payroll.bank_transfer import (
    PaymentFileStatus,
    PaymentType,
    TransferStatus,
)
from schema.Payroll.bank_transfer import (
    BankReconciliationCreate,
    BankReconciliationEntryResponse,
    BankReconciliationEntryUpdate,
    BankReconciliationResponse,
    BankReconciliationVerify,
    BankTransferCreate,
    BankTransferResponse,
    BankTransferUpdate,
    BulkStatusUpdateRequest,
    DashboardSummaryResponse,
    ExportRequest,
    GeneratePaymentFileRequest,
    PaymentAnalyticsResponse,
    PaymentFileCreate,
    PaymentFileEntryResponse,
    PaymentFileEntryUpdate,
    PaymentFileResponse,
    PaymentFileUpdate,
    PaymentSettingsResponse,
    PaymentSettingsUpsert,
    PendingPaymentCreate,
    PendingPaymentResolve,
    PendingPaymentResponse,
    TransferStatusPayload,
)
from services.Payroll.bank_transfer_service import (
    BankReconciliationService,
    BankTransferService,
    PaymentAnalyticsService,
    PaymentFileEntryService,
    PaymentFileService,
    PaymentSettingsService,
    PendingPaymentService,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/bank-transfer",
    tags=["Payroll – Bank Transfer & Payment Processing"],
)


@router.post(
    "/payment-files/",
    response_model=PaymentFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a payment file",
    description=(
        "Manually create a new bank payment file record. "
        "For auto-generation from a payroll run use POST /payment-files/generate."
    ),
)
def create_payment_file(
    payload: PaymentFileCreate,
    db: Session = Depends(get_db),
):
    return PaymentFileService.create(db, payload)


@router.post(
    "/payment-files/generate",
    response_model=List[PaymentFileResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Generate Payment Files from a Payroll Run",
    description=(
        "Reads all PayrollRunDetail rows for the given run and auto-creates "
        "one PaymentFile per bank, plus individual PaymentFileEntry rows. "
        "Corresponds to the 'Generate Payment File' button in the UI."
    ),
)
def generate_payment_files(
    req: GeneratePaymentFileRequest,
    db: Session = Depends(get_db),
):
    return PaymentFileService.generate_from_payroll_run(db, req)


@router.get(
    "/payment-files/",
    response_model=List[PaymentFileResponse],
    summary="List all payment files",
    description="Supports filtering by bank_name, status, payment_type, and date range.",
)
def list_payment_files(
    bank_name: Optional[str] = Query(None, description="Filter by bank name (partial match)"),
    file_status: Optional[PaymentFileStatus] = Query(None, alias="status"),
    payment_type: Optional[PaymentType] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows, _total = PaymentFileService.list_all(
        db,
        bank_name=bank_name,
        status=file_status,
        payment_type=payment_type,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return rows


@router.get(
    "/payment-files/{file_id}",
    response_model=PaymentFileResponse,
    summary="Get a payment file by ID",
)
def get_payment_file(file_id: int, db: Session = Depends(get_db)):
    return PaymentFileService.get_by_id(db, file_id)


@router.put(
    "/payment-files/{file_id}",
    response_model=PaymentFileResponse,
    summary="Update a payment file",
)
def update_payment_file(
    file_id: int,
    payload: PaymentFileUpdate,
    db: Session = Depends(get_db),
):
    return PaymentFileService.update(db, file_id, payload)


@router.patch(
    "/payment-files/{file_id}/approve",
    response_model=PaymentFileResponse,
    summary="Approve / initiate a payment file",
    description="Transitions status to Processed and records the approver.",
)
def approve_payment_file(
    file_id: int,
    approved_by: int = Query(..., description="Employee ID of the approver"),
    db: Session = Depends(get_db),
):
    return PaymentFileService.approve(db, file_id, approved_by)


@router.delete(
    "/payment-files/{file_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a payment file (non-Processed only)",
)
def delete_payment_file(file_id: int, db: Session = Depends(get_db)):
    PaymentFileService.delete(db, file_id)



@router.get(
    "/payment-files/{file_id}/export/csv",
    summary="Export payment file entries as CSV",
    description="Returns a CSV of all entries in the payment file. Corresponds to Export CSV button.",
)
def export_payment_file_csv(file_id: int, db: Session = Depends(get_db)):
    csv_content = PaymentFileService.export_csv(db, file_id)
    pf = PaymentFileService.get_by_id(db, file_id)
    filename = f"{pf.file_name}.csv"
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )



@router.get(
    "/payment-files/{file_id}/entries/",
    response_model=List[PaymentFileEntryResponse],
    summary="List entries for a payment file",
)
def list_payment_file_entries(
    file_id: int,
    entry_status: Optional[TransferStatus] = Query(None, alias="status"),
    db: Session = Depends(get_db),
):
    return PaymentFileEntryService.list_by_file(db, file_id, status=entry_status)


@router.patch(
    "/payment-files/entries/{entry_id}",
    response_model=PaymentFileEntryResponse,
    summary="Update a single payment file entry",
)
def update_payment_file_entry(
    entry_id: int,
    payload: PaymentFileEntryUpdate,
    db: Session = Depends(get_db),
):
    return PaymentFileEntryService.update_entry(db, entry_id, payload)


@router.post(
    "/payment-files/entries/bulk-update",
    response_model=List[PaymentFileEntryResponse],
    summary="Bulk update statuses of multiple entries",
    description="Corresponds to Bulk Actions dropdown in the UI.",
)
def bulk_update_entry_statuses(
    req: BulkStatusUpdateRequest,
    db: Session = Depends(get_db),
):
    return PaymentFileEntryService.bulk_update_status(db, req)


@router.patch(
    "/payment-files/entries/{entry_id}/retry",
    response_model=PaymentFileEntryResponse,
    summary="Retry a failed / cancelled payment file entry",
)
def retry_payment_file_entry(entry_id: int, db: Session = Depends(get_db)):
    return PaymentFileEntryService.retry_entry(db, entry_id)



@router.post(
    "/transfers/",
    response_model=BankTransferResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a bank transfer record",
)
def create_bank_transfer(
    payload: BankTransferCreate,
    db: Session = Depends(get_db),
):
    return BankTransferService.create(db, payload)


@router.get(
    "/transfers/",
    response_model=List[BankTransferResponse],
    summary="List bank transfers with filters",
    description=(
        "Supports filtering by employee_id, payroll_run_id, payment_file_id, "
        "status, bank_name, and date range. Results paginated."
    ),
)
def list_bank_transfers(
    employee_id: Optional[int] = Query(None),
    payroll_run_id: Optional[int] = Query(None),
    payment_file_id: Optional[int] = Query(None),
    transfer_status: Optional[TransferStatus] = Query(None, alias="status"),
    bank_name: Optional[str] = Query(None),
    date_from: Optional[datetime] = Query(None),
    date_to: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows, _total = BankTransferService.list_all(
        db,
        employee_id=employee_id,
        payroll_run_id=payroll_run_id,
        payment_file_id=payment_file_id,
        status=transfer_status,
        bank_name=bank_name,
        date_from=date_from,
        date_to=date_to,
        skip=skip,
        limit=limit,
    )
    return rows


@router.get(
    "/transfers/{transfer_id}",
    response_model=BankTransferResponse,
    summary="Get a bank transfer by ID",
)
def get_bank_transfer(transfer_id: int, db: Session = Depends(get_db)):
    return BankTransferService.get_by_id(db, transfer_id)


@router.put(
    "/transfers/{transfer_id}",
    response_model=BankTransferResponse,
    summary="Update a bank transfer",
)
def update_bank_transfer(
    transfer_id: int,
    payload: BankTransferUpdate,
    db: Session = Depends(get_db),
):
    return BankTransferService.update(db, transfer_id, payload)


@router.patch(
    "/transfers/{transfer_id}/mark-success",
    response_model=BankTransferResponse,
    summary="Mark a transfer as Successful",
    description="Optionally records the UTR number returned by the bank.",
)
def mark_transfer_success(
    transfer_id: int,
    payload: TransferStatusPayload,
    db: Session = Depends(get_db),
):
    return BankTransferService.mark_success(db, transfer_id, payload)


@router.patch(
    "/transfers/{transfer_id}/mark-failed",
    response_model=BankTransferResponse,
    summary="Mark a transfer as Failed",
)
def mark_transfer_failed(
    transfer_id: int,
    payload: TransferStatusPayload,
    db: Session = Depends(get_db),
):
    return BankTransferService.mark_failed(db, transfer_id, payload)


@router.patch(
    "/transfers/{transfer_id}/retry",
    response_model=BankTransferResponse,
    summary="Retry a failed transfer",
    description="Increments retry count and resets status to Pending.",
)
def retry_bank_transfer(transfer_id: int, db: Session = Depends(get_db)):
    return BankTransferService.retry(db, transfer_id)


@router.delete(
    "/transfers/{transfer_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a bank transfer (non-successful only)",
)
def delete_bank_transfer(transfer_id: int, db: Session = Depends(get_db)):
    BankTransferService.delete(db, transfer_id)


@router.post(
    "/pending-payments/",
    response_model=PendingPaymentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a pending payment record",
)
def create_pending_payment(
    payload: PendingPaymentCreate,
    db: Session = Depends(get_db),
):
    return PendingPaymentService.create(db, payload)


@router.get(
    "/pending-payments/",
    response_model=List[PendingPaymentResponse],
    summary="List pending payments",
    description=(
        "By default returns only unresolved payments. "
        "Pass is_resolved=true to see resolved ones too. "
        "Corresponds to the 'Pending Payments (N)' section in the UI."
    ),
)
def list_pending_payments(
    is_resolved: Optional[bool] = Query(False),
    payment_file_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    rows, _total = PendingPaymentService.list_all(
        db, is_resolved=is_resolved, payment_file_id=payment_file_id,
        skip=skip, limit=limit,
    )
    return rows


@router.patch(
    "/pending-payments/{pending_id}/resolve",
    response_model=PendingPaymentResponse,
    summary="Mark a pending payment as resolved",
)
def resolve_pending_payment(
    pending_id: int,
    payload: PendingPaymentResolve,
    db: Session = Depends(get_db),
):
    return PendingPaymentService.resolve(
        db, pending_id,
        resolved_by=payload.resolved_by or 0,
        note=payload.resolution_note,
    )


@router.patch(
    "/pending-payments/{pending_id}/retry",
    response_model=PendingPaymentResponse,
    summary="Retry a pending payment",
    description="Increments retry_count. Returns 400 when max_retries exceeded.",
)
def retry_pending_payment(pending_id: int, db: Session = Depends(get_db)):
    return PendingPaymentService.retry(db, pending_id)


@router.get(
    "/pending-payments/download-report",
    summary="Download Pending Report as CSV",
    description="Corresponds to the 'Download Pending Report' quick-action button.",
)
def download_pending_report(db: Session = Depends(get_db)):
    csv_content = PendingPaymentService.download_pending_report(db)
    return StreamingResponse(
        io.StringIO(csv_content),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="pending_payments_report.csv"'},
    )


@router.get(
    "/settings/",
    response_model=PaymentSettingsResponse,
    summary="Get current payment settings",
    description=(
        "Returns the org-level payment settings (auto-encryption, notifications, "
        "default payment type, data retention, etc.). Bootstraps defaults on first call."
    ),
)
def get_payment_settings(db: Session = Depends(get_db)):
    return PaymentSettingsService.get(db)


@router.put(
    "/settings/",
    response_model=PaymentSettingsResponse,
    summary="Save payment settings",
    description="Upsert org-level payment settings. Maps to the 'Save Settings' button in the UI.",
)
def save_payment_settings(
    payload: PaymentSettingsUpsert,
    db: Session = Depends(get_db),
):
    return PaymentSettingsService.upsert(db, payload)


@router.post(
    "/reconciliation/run",
    response_model=BankReconciliationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Run bank reconciliation",
    description=(
        "Creates a new reconciliation session and auto-matches transfers "
        "against expected payments for the given payment_file_id. "
        "Corresponds to 'Run Reconciliation' button in the UI."
    ),
)
def run_reconciliation(
    payload: BankReconciliationCreate,
    db: Session = Depends(get_db),
):
    return BankReconciliationService.run_reconciliation(db, payload)


@router.get(
    "/reconciliation/",
    response_model=List[BankReconciliationResponse],
    summary="List reconciliation sessions",
)
def list_reconciliations(
    payment_file_id: Optional[int] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    rows, _total = BankReconciliationService.list_all(
        db, payment_file_id=payment_file_id, skip=skip, limit=limit
    )
    return rows


@router.get(
    "/reconciliation/{recon_id}",
    response_model=BankReconciliationResponse,
    summary="Get a reconciliation session by ID",
)
def get_reconciliation(recon_id: int, db: Session = Depends(get_db)):
    return BankReconciliationService.get_by_id(db, recon_id)


@router.patch(
    "/reconciliation/{recon_id}/verify",
    response_model=BankReconciliationResponse,
    summary="Verify / sign off a reconciliation session",
)
def verify_reconciliation(
    recon_id: int,
    payload: BankReconciliationVerify,
    db: Session = Depends(get_db),
):
    return BankReconciliationService.verify(db, recon_id, payload.verified_by, payload.notes)


@router.patch(
    "/reconciliation/{recon_id}/mark-all-verified",
    response_model=BankReconciliationResponse,
    summary="Mark all pending entries as Matched and verify the session",
    description="Corresponds to 'Mark All Verified' button in Bank Statement Reconciliation modal.",
)
def mark_all_verified(recon_id: int, db: Session = Depends(get_db)):
    return BankReconciliationService.mark_all_verified(db, recon_id)


@router.get(
    "/reconciliation/{recon_id}/entries/",
    response_model=List[BankReconciliationEntryResponse],
    summary="List reconciliation entries for a session",
)
def list_reconciliation_entries(recon_id: int, db: Session = Depends(get_db)):
    return BankReconciliationService.get_entries(db, recon_id)


@router.patch(
    "/reconciliation/entries/{entry_id}",
    response_model=BankReconciliationEntryResponse,
    summary="Update a reconciliation entry (override status / mismatch reason)",
)
def update_reconciliation_entry(
    entry_id: int,
    payload: BankReconciliationEntryUpdate,
    db: Session = Depends(get_db),
):
    return BankReconciliationService.update_entry(db, entry_id, payload)


@router.get(
    "/reconciliation/{recon_id}/export",
    summary="Export reconciliation report as CSV",
    description="Corresponds to 'Export Report' button in Bank Statement Reconciliation modal.",
)
def export_reconciliation_report(recon_id: int, db: Session = Depends(get_db)):
    import csv, io as _io
    entries = BankReconciliationService.get_entries(db, recon_id)
    out = _io.StringIO()
    writer = csv.writer(out)
    writer.writerow(
        ["Transaction ID", "Reference", "Employee Code", "Employee Name",
         "Bank", "Account", "Expected Amount", "Actual Amount", "Status", "Mismatch Reason", "Date"]
    )
    for e in entries:
        writer.writerow(
            [e.transaction_id, e.reference_number or "", e.employee_code or "",
             e.employee_name, e.bank_name or "", e.bank_account or "",
             e.expected_amount, e.actual_amount,
             e.status.value if hasattr(e.status, "value") else e.status,
             e.mismatch_reason or "", e.statement_date or ""]
        )
    return StreamingResponse(
        _io.StringIO(out.getvalue()),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="reconciliation_{recon_id}.csv"'},
    )



@router.get(
    "/analytics/summary",
    response_model=DashboardSummaryResponse,
    summary="Dashboard summary KPI cards",
    description=(
        "Returns the four top-level KPI cards: Total Processed, Successful, "
        "Pending (Require Action), Failed (Need Retry). "
        "Corresponds to the stat cards in the Bank Transfer & Payment Processing page."
    ),
)
def get_dashboard_summary(db: Session = Depends(get_db)):
    return PaymentAnalyticsService.get_dashboard_summary(db)


@router.get(
    "/analytics/",
    response_model=PaymentAnalyticsResponse,
    summary="Full payment analytics panel",
    description=(
        "Returns all data shown in the Payment Analytics modal: total amount, "
        "success rate, monthly trends, bank-wise distribution, payment type "
        "distribution, and transaction status breakdown. "
        "Corresponds to 'View Analytics' quick-action button."
    ),
)
def get_payment_analytics(
    months: int = Query(4, ge=1, le=12, description="Number of historical months to include"),
    db: Session = Depends(get_db),
):
    return PaymentAnalyticsService.get_analytics(db, months=months)