from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional

from core.database import get_db
from schema.Payroll.bank_transfer import (
    BankTransferSettingsUpdate,
    BankTransferSettingsResponse,
    PaymentFileCreate,
    PaymentFileUpdate,
    PaymentFileResponse,
    PaymentTransactionCreate,
    PaymentTransactionUpdate,
    PaymentTransactionResponse,
    BankReconciliationResponse,
    ReconciliationSummary,
    BankTransferDashboard,
    PaymentAnalytics,
)
#import services.Payroll.bank_transfer as svc

router = APIRouter(
    prefix="/bank-transfer",
    tags=["Payroll-Bank Transfer"],
)


# ══════════════════════════════════════════════════════════════════════════════
#  STATIC ROUTES — before /{id} paths
# ══════════════════════════════════════════════════════════════════════════════

# ── Dashboard (4 cards) ───────────────────────────────────────────────────────

@router.get(
    "/dashboard",
    response_model=BankTransferDashboard,
    summary="Dashboard — Total Processed, Successful, Pending, Failed",
)
def get_dashboard(db: Session = Depends(get_db)):
    return svc.get_dashboard(db)


# ── Payment Analytics modal ───────────────────────────────────────────────────

@router.get(
    "/analytics",
    response_model=PaymentAnalytics,
    summary="Payment Analytics — Total Amount, Success Rate, Transactions, Monthly Trends",
)
def get_analytics(db: Session = Depends(get_db)):
    return svc.get_analytics(db)


# ── Pending Payments section ──────────────────────────────────────────────────

@router.get(
    "/pending-payments",
    response_model=List[PaymentTransactionResponse],
    summary="Pending Payments — requires immediate attention",
)
def get_pending_payments(db: Session = Depends(get_db)):
    return svc.get_pending_transactions(db)


# ── Download Pending Report ───────────────────────────────────────────────────

@router.get(
    "/pending-payments/download",
    summary="Download Pending Report button",
)
def download_pending_report():
    return {"message": "Pending report download coming soon"}


# ── Export CSV / PDF ──────────────────────────────────────────────────────────

@router.get("/export/csv", summary="Export CSV — Quick Action button")
def export_csv():
    return {"message": "CSV export coming soon"}


@router.get("/export/pdf", summary="Export PDF — Quick Action button")
def export_pdf():
    return {"message": "PDF export coming soon"}


# ── Settings modal ────────────────────────────────────────────────────────────

@router.get(
    "/settings",
    response_model=BankTransferSettingsResponse,
    summary="Get payment settings",
)
def get_settings(db: Session = Depends(get_db)):
    return svc.get_settings(db)


@router.put(
    "/settings",
    response_model=BankTransferSettingsResponse,
    summary="Save Settings button — update payment settings",
)
def update_settings(
    payload: BankTransferSettingsUpdate,
    db: Session = Depends(get_db),
):
    return svc.update_settings(db, payload)


# ── Filter / Search payment files ─────────────────────────────────────────────

@router.get(
    "/files/filter",
    response_model=List[PaymentFileResponse],
    summary="Filter/search payment files — All Banks, All Status dropdowns",
)
def filter_files(
    bank_name: Optional[str] = None,
    status: Optional[str]    = None,
    search: Optional[str]    = None,
    db: Session = Depends(get_db),
):
    return svc.get_all_files(db, bank_name=bank_name, status=status, search=search)


# ── Export All payment files ──────────────────────────────────────────────────

@router.get("/files/export-all", summary="Export All button")
def export_all_files():
    return {"message": "Export All coming soon"}


# ══════════════════════════════════════════════════════════════════════════════
#  PAYMENT FILES
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/files",
    response_model=List[PaymentFileResponse],
    summary="List all payment files",
)
def get_all_files(db: Session = Depends(get_db)):
    return svc.get_all_files(db)


@router.post(
    "/files",
    response_model=PaymentFileResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Generate Payment File — + Generate Payment File button",
)
def create_file(
    payload: PaymentFileCreate,
    db: Session = Depends(get_db),
):
    return svc.create_file(db, payload)


@router.get(
    "/files/{file_id}",
    response_model=PaymentFileResponse,
    summary="View a payment file (eye icon)",
)
def get_file(file_id: int, db: Session = Depends(get_db)):
    pf = svc.get_file_by_id(db, file_id)
    if not pf:
        raise HTTPException(status_code=404, detail="Payment file not found")
    return pf


@router.put(
    "/files/{file_id}",
    response_model=PaymentFileResponse,
    summary="Update a payment file",
)
def update_file(
    file_id: int,
    payload: PaymentFileUpdate,
    db: Session = Depends(get_db),
):
    pf = svc.update_file(db, file_id, payload)
    if not pf:
        raise HTTPException(status_code=404, detail="Payment file not found")
    return pf


@router.delete("/files/{file_id}", summary="Delete a payment file (trash icon)")
def delete_file(file_id: int, db: Session = Depends(get_db)):
    if not svc.delete_file(db, file_id):
        raise HTTPException(status_code=404, detail="Payment file not found")
    return {"message": "Payment file deleted successfully"}


# ── Process / Retry file ──────────────────────────────────────────────────────

@router.put(
    "/files/{file_id}/process",
    response_model=PaymentFileResponse,
    summary="Mark a payment file as processed",
)
def process_file(file_id: int, db: Session = Depends(get_db)):
    pf, error = svc.process_file(db, file_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return pf


@router.put(
    "/files/{file_id}/retry",
    response_model=PaymentFileResponse,
    summary="Retry failed transactions in a file (retry icon)",
)
def retry_file(file_id: int, db: Session = Depends(get_db)):
    pf, error = svc.retry_file(db, file_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return pf


# ── Download a file ───────────────────────────────────────────────────────────

@router.get(
    "/files/{file_id}/download",
    summary="Download payment file (download icon)",
)
def download_file(file_id: int, db: Session = Depends(get_db)):
    pf = svc.get_file_by_id(db, file_id)
    if not pf:
        raise HTTPException(status_code=404, detail="Payment file not found")
    return {"message": f"Download for {pf.file_name} coming soon", "file_id": file_id}


# ══════════════════════════════════════════════════════════════════════════════
#  PAYMENT TRANSACTIONS
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/files/{file_id}/transactions",
    response_model=List[PaymentTransactionResponse],
    summary="List all transactions within a payment file",
)
def get_transactions(file_id: int, db: Session = Depends(get_db)):
    return svc.get_transactions(db, payment_file_id=file_id)


@router.post(
    "/transactions",
    response_model=PaymentTransactionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a payment transaction to a file",
)
def create_transaction(
    payload: PaymentTransactionCreate,
    db: Session = Depends(get_db),
):
    return svc.create_transaction(db, payload)


@router.put(
    "/transactions/{transaction_id}/retry",
    response_model=PaymentTransactionResponse,
    summary="Retry a single failed transaction (retry icon in Pending Payments)",
)
def retry_transaction(transaction_id: int, db: Session = Depends(get_db)):
    txn, error = svc.retry_transaction(db, transaction_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return txn


@router.put(
    "/transactions/{transaction_id}/fail",
    response_model=PaymentTransactionResponse,
    summary="Mark a transaction as failed with a reason",
)
def fail_transaction(
    transaction_id: int,
    failure_reason: str,
    db: Session = Depends(get_db),
):
    txn, error = svc.mark_transaction_failed(db, transaction_id, failure_reason)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return txn


# ══════════════════════════════════════════════════════════════════════════════
#  BANK RECONCILIATION modal
# ══════════════════════════════════════════════════════════════════════════════

@router.get(
    "/files/{file_id}/reconciliation",
    response_model=ReconciliationSummary,
    summary="Bank Statement Reconciliation modal — summary + details",
)
def get_reconciliation(file_id: int, db: Session = Depends(get_db)):
    pf = svc.get_file_by_id(db, file_id)
    if not pf:
        raise HTTPException(status_code=404, detail="Payment file not found")
    return svc.get_reconciliation_summary(db, file_id)


@router.put(
    "/files/{file_id}/reconciliation/run",
    response_model=ReconciliationSummary,
    summary="Run Reconciliation button — auto-match transactions",
)
def run_reconciliation(file_id: int, db: Session = Depends(get_db)):
    summary, error = svc.run_reconciliation(db, file_id)
    if error:
        raise HTTPException(status_code=400, detail=error)
    return summary