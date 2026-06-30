
from __future__ import annotations

import csv
import io
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Tuple

from fastapi import HTTPException, status
from sqlalchemy import and_, func, or_, select
from sqlalchemy.orm import Session

from model.Payroll.bank_transfer import (
    BankReconciliation,
    BankReconciliationEntry,
    BankTransfer,
    PaymentFile,
    PaymentFileEntry,
    PaymentFileStatus,
    PaymentSettings,
    PaymentType,
    PendingPayment,
    ReconciliationStatus,
    TransferStatus,
)
from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from schema.Payroll.bank_transfer import (
    BankDistributionItem,
    BankReconciliationCreate,
    BankReconciliationEntryCreate,
    BankReconciliationEntryUpdate,
    BankTransferCreate,
    BankTransferUpdate,
    BulkStatusUpdateRequest,
    DashboardSummaryResponse,
    GeneratePaymentFileRequest,
    MonthlyTrendItem,
    PaymentAnalyticsResponse,
    PaymentFileCreate,
    PaymentFileEntryUpdate,
    PaymentFileUpdate,
    PaymentSettingsUpsert,
    PaymentTypeDistributionItem,
    PendingPaymentCreate,
    TransactionStatusSummary,
    TransferStatusPayload,
)

logger = logging.getLogger(__name__)



def _get_or_404(db: Session, model, pk: int, label: str):

    obj = db.get(model, pk)
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"{label} not found")
    return obj


def _apply_filters(stmt, model, filters: Dict[str, Any]):

    for field, value in filters.items():
        if value is None:
            continue
        if field == "date_from":
            stmt = stmt.where(model.created_at >= value)
        elif field == "date_to":
            stmt = stmt.where(model.created_at <= value)
        elif hasattr(model, field):
            stmt = stmt.where(getattr(model, field) == value)
    return stmt


class PaymentFileService:

    @staticmethod
    def create(db: Session, payload: PaymentFileCreate, generated_by: Optional[int] = None) -> PaymentFile:
        # Guard: batch_reference must be unique
        existing = db.execute(
            select(PaymentFile).where(PaymentFile.batch_reference == payload.batch_reference)
        ).scalar_one_or_none()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Payment file with batch reference '{payload.batch_reference}' already exists",
            )

        obj = PaymentFile(**payload.model_dump(), generated_by=generated_by)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        logger.info("PaymentFile created id=%s batch=%s", obj.id, obj.batch_reference)
        return obj

    @staticmethod
    def list_all(
        db: Session,
        bank_name: Optional[str] = None,
        status: Optional[PaymentFileStatus] = None,
        payment_type: Optional[PaymentType] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[PaymentFile], int]:
        stmt = select(PaymentFile)
        if bank_name:
            stmt = stmt.where(PaymentFile.bank_name.ilike(f"%{bank_name}%"))
        if status:
            stmt = stmt.where(PaymentFile.status == status)
        if payment_type:
            stmt = stmt.where(PaymentFile.payment_type == payment_type)
        if date_from:
            stmt = stmt.where(PaymentFile.generated_date >= date_from)
        if date_to:
            stmt = stmt.where(PaymentFile.generated_date <= date_to)

        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = db.execute(
            stmt.order_by(PaymentFile.generated_date.desc()).offset(skip).limit(limit)
        ).scalars().all()
        return rows, total

    @staticmethod
    def get_by_id(db: Session, file_id: int) -> PaymentFile:
        return _get_or_404(db, PaymentFile, file_id, "Payment file")

    @staticmethod
    def update(db: Session, file_id: int, payload: PaymentFileUpdate) -> PaymentFile:
        obj = _get_or_404(db, PaymentFile, file_id, "Payment file")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def approve(db: Session, file_id: int, approved_by: int) -> PaymentFile:
        obj = _get_or_404(db, PaymentFile, file_id, "Payment file")
        if obj.status not in (PaymentFileStatus.GENERATED, PaymentFileStatus.PENDING):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only Generated or Pending files can be approved",
            )
        obj.approved_by = approved_by
        obj.approved_at = datetime.utcnow()
        obj.status = PaymentFileStatus.PROCESSED
        obj.processed_date = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        logger.info("PaymentFile %s approved by employee %s", file_id, approved_by)
        return obj

    @staticmethod
    def delete(db: Session, file_id: int) -> None:
        obj = _get_or_404(db, PaymentFile, file_id, "Payment file")
        if obj.status == PaymentFileStatus.PROCESSED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete a Processed payment file",
            )
        db.delete(obj)
        db.commit()
        logger.info("PaymentFile %s deleted", file_id)

    @staticmethod
    def generate_from_payroll_run(
        db: Session,
        req: GeneratePaymentFileRequest,
        generated_by: Optional[int] = None,
    ) -> List[PaymentFile]:

        run = _get_or_404(db, PayrollRun, req.payroll_run_id, "PayrollRun")

        details_stmt = select(PayrollRunDetail).where(
            PayrollRunDetail.payroll_run_id == req.payroll_run_id
        )
        details: List[PayrollRunDetail] = db.execute(details_stmt).scalars().all()
        if not details:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="No payroll run details found for this run",
            )

        settings = db.execute(select(PaymentSettings)).scalar_one_or_none()
        default_payment_type = (
            req.payment_type
            or (settings.default_payment_type if settings else PaymentType.NEFT)
        )

        bank_groups: Dict[str, List[PayrollRunDetail]] = {}
        for d in details:
          
            bank = getattr(d, "bank_name", None) or "ALL"
            if req.bank_names and bank not in req.bank_names and bank != "ALL":
                continue
            bank_groups.setdefault(bank, []).append(d)

        created_files: List[PaymentFile] = []
        month_str = f"{run.run_year}{run.run_month:02d}"

        for bank_name, group in bank_groups.items():
            bank_code = bank_name.replace(" ", "_").upper()[:10]
            batch_ref = f"BATCH-{month_str}-{bank_code}-{run.id}"
            ref_num = f"REF{month_str}{bank_code}{run.id:03d}"
            file_name = f"SALARY_{month_str}_{bank_code}"

            total = sum(Decimal(str(d.net_pay)) for d in group)
            category = "Salary" 

            pf = PaymentFile(
                file_name=file_name,
                batch_reference=batch_ref,
                reference_number=ref_num,
                payroll_run_id=req.payroll_run_id,
                bank_name=bank_name,
                bank_code=bank_code,
                payment_type=default_payment_type,
                payment_category="Salary",
                total_amount=total,
                total_employees=len(group),
                value_date=req.value_date,
                remarks=req.remarks,
                generated_by=generated_by,
                status=PaymentFileStatus.GENERATED,
            )
            db.add(pf)
            db.flush()

            for d in group:
                entry = PaymentFileEntry(
                    payment_file_id=pf.id,
                    employee_id=d.employee_id,
                    employee_code=d.employee_code,
                    employee_name=d.employee_name,
                    department=d.department,
                    designation=d.designation,
                    bank_name=bank_name,
                    bank_account="UNKNOWN",   
                    ifsc_code="UNKNOWN",
                    gross_salary=d.gross_salary,
                    deductions=d.total_deductions,
                    net_pay=d.net_pay,
                    status=TransferStatus.PENDING,
                )
                db.add(entry)

            created_files.append(pf)

        db.commit()
        for pf in created_files:
            db.refresh(pf)

        logger.info(
            "Generated %d payment files for payroll run %s",
            len(created_files),
            req.payroll_run_id,
        )
        return created_files

    @staticmethod
    def export_csv(db: Session, file_id: int) -> str:

        pf = _get_or_404(db, PaymentFile, file_id, "Payment file")
        entries = db.execute(
            select(PaymentFileEntry).where(PaymentFileEntry.payment_file_id == file_id)
        ).scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "Employee Code", "Employee Name", "Department",
                "Bank Name", "Account Number", "IFSC Code",
                "Gross Salary", "Deductions", "Net Pay",
                "Status", "UTR Number", "Transfer Date",
            ]
        )
        for e in entries:
            writer.writerow(
                [
                    e.employee_code, e.employee_name, e.department or "",
                    e.bank_name, e.bank_account, e.ifsc_code,
                    e.gross_salary, e.deductions, e.net_pay,
                    e.status.value if hasattr(e.status, "value") else e.status,
                    e.utr_number or "", e.transfer_date or "",
                ]
            )
        return output.getvalue()



class PaymentFileEntryService:

    @staticmethod
    def list_by_file(
        db: Session,
        file_id: int,
        status: Optional[TransferStatus] = None,
    ) -> List[PaymentFileEntry]:
        stmt = select(PaymentFileEntry).where(PaymentFileEntry.payment_file_id == file_id)
        if status:
            stmt = stmt.where(PaymentFileEntry.status == status)
        return db.execute(stmt.order_by(PaymentFileEntry.id)).scalars().all()

    @staticmethod
    def update_entry(
        db: Session, entry_id: int, payload: PaymentFileEntryUpdate
    ) -> PaymentFileEntry:
        obj = _get_or_404(db, PaymentFileEntry, entry_id, "Payment file entry")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def bulk_update_status(db: Session, req: BulkStatusUpdateRequest) -> List[PaymentFileEntry]:
        entries = db.execute(
            select(PaymentFileEntry).where(PaymentFileEntry.id.in_(req.entry_ids))
        ).scalars().all()
        if not entries:
            raise HTTPException(status_code=404, detail="No matching entries found")

        for e in entries:
            e.status = req.status
            if req.utr_number:
                e.utr_number = req.utr_number
            if req.failure_reason:
                e.failure_reason = req.failure_reason
            e.updated_at = datetime.utcnow()

        db.commit()
        for e in entries:
            db.refresh(e)
        return entries

    @staticmethod
    def retry_entry(db: Session, entry_id: int) -> PaymentFileEntry:
        obj = _get_or_404(db, PaymentFileEntry, entry_id, "Payment file entry")
        if obj.status not in (TransferStatus.FAILED, TransferStatus.CANCELLED):
            raise HTTPException(
                status_code=400,
                detail="Only Failed or Cancelled entries can be retried",
            )
        obj.status = TransferStatus.PENDING
        obj.retry_count += 1
        obj.failure_reason = None
        obj.utr_number = None
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj



class BankTransferService:

    @staticmethod
    def create(db: Session, payload: BankTransferCreate) -> BankTransfer:
        obj = BankTransfer(**payload.model_dump())
        if payload.initiated_by:
            obj.initiated_at = datetime.utcnow()
        db.add(obj)
        db.commit()
        db.refresh(obj)
        logger.info("BankTransfer created id=%s emp=%s amount=%s", obj.id, obj.employee_id, obj.transfer_amount)
        return obj

    @staticmethod
    def list_all(
        db: Session,
        employee_id: Optional[int] = None,
        payroll_run_id: Optional[int] = None,
        payment_file_id: Optional[int] = None,
        status: Optional[TransferStatus] = None,
        bank_name: Optional[str] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[BankTransfer], int]:
        stmt = select(BankTransfer)
        if employee_id:
            stmt = stmt.where(BankTransfer.employee_id == employee_id)
        if payroll_run_id:
            stmt = stmt.where(BankTransfer.payroll_run_id == payroll_run_id)
        if payment_file_id:
            stmt = stmt.where(BankTransfer.payment_file_id == payment_file_id)
        if status:
            stmt = stmt.where(BankTransfer.status == status)
        if bank_name:
            stmt = stmt.where(BankTransfer.bank_name.ilike(f"%{bank_name}%"))
        if date_from:
            stmt = stmt.where(BankTransfer.transfer_date >= date_from)
        if date_to:
            stmt = stmt.where(BankTransfer.transfer_date <= date_to)

        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = db.execute(
            stmt.order_by(BankTransfer.transfer_date.desc()).offset(skip).limit(limit)
        ).scalars().all()
        return rows, total

    @staticmethod
    def get_by_id(db: Session, transfer_id: int) -> BankTransfer:
        return _get_or_404(db, BankTransfer, transfer_id, "Bank transfer")

    @staticmethod
    def update(db: Session, transfer_id: int, payload: BankTransferUpdate) -> BankTransfer:
        obj = _get_or_404(db, BankTransfer, transfer_id, "Bank transfer")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def mark_success(
        db: Session, transfer_id: int, payload: TransferStatusPayload
    ) -> BankTransfer:
        obj = _get_or_404(db, BankTransfer, transfer_id, "Bank transfer")
        if obj.status == TransferStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Transfer is already marked as Success")
        obj.status = TransferStatus.SUCCESS
        obj.completed_at = datetime.utcnow()
        if payload.utr_number:
            obj.utr_number = payload.utr_number
        if payload.remarks:
            obj.remarks = payload.remarks
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        logger.info("BankTransfer %s marked SUCCESS utr=%s", transfer_id, obj.utr_number)
        return obj

    @staticmethod
    def mark_failed(
        db: Session, transfer_id: int, payload: TransferStatusPayload
    ) -> BankTransfer:
        obj = _get_or_404(db, BankTransfer, transfer_id, "Bank transfer")
        if obj.status == TransferStatus.FAILED:
            raise HTTPException(status_code=400, detail="Transfer is already marked as Failed")
        obj.status = TransferStatus.FAILED
        obj.failure_reason = payload.failure_reason
        if payload.remarks:
            obj.remarks = payload.remarks
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        logger.info("BankTransfer %s marked FAILED reason=%s", transfer_id, payload.failure_reason)
        return obj

    @staticmethod
    def retry(db: Session, transfer_id: int) -> BankTransfer:
        obj = _get_or_404(db, BankTransfer, transfer_id, "Bank transfer")
        if obj.status not in (TransferStatus.FAILED, TransferStatus.CANCELLED):
            raise HTTPException(
                status_code=400,
                detail="Only Failed or Cancelled transfers can be retried",
            )
        obj.status = TransferStatus.PENDING
        obj.retry_count += 1
        obj.last_retry_at = datetime.utcnow()
        obj.failure_reason = None
        obj.utr_number = None
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def delete(db: Session, transfer_id: int) -> None:
        obj = _get_or_404(db, BankTransfer, transfer_id, "Bank transfer")
        if obj.status == TransferStatus.SUCCESS:
            raise HTTPException(status_code=400, detail="Cannot delete a successful transfer")
        db.delete(obj)
        db.commit()



class PendingPaymentService:

    @staticmethod
    def create(db: Session, payload: PendingPaymentCreate) -> PendingPayment:
        obj = PendingPayment(**payload.model_dump())
        db.add(obj)
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def list_all(
        db: Session,
        is_resolved: Optional[bool] = False,
        payment_file_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[PendingPayment], int]:
        stmt = select(PendingPayment)
        if is_resolved is not None:
            stmt = stmt.where(PendingPayment.is_resolved == is_resolved)
        if payment_file_id:
            stmt = stmt.where(PendingPayment.payment_file_id == payment_file_id)

        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = db.execute(
            stmt.order_by(PendingPayment.days_pending.desc()).offset(skip).limit(limit)
        ).scalars().all()
        return rows, total

    @staticmethod
    def resolve(db: Session, pending_id: int, resolved_by: int, note: Optional[str] = None) -> PendingPayment:
        obj = _get_or_404(db, PendingPayment, pending_id, "Pending payment")
        if obj.is_resolved:
            raise HTTPException(status_code=400, detail="Payment already resolved")
        obj.is_resolved = True
        obj.resolved_at = datetime.utcnow()
        obj.resolved_by = resolved_by
        obj.resolution_note = note
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def retry(db: Session, pending_id: int) -> PendingPayment:
        obj = _get_or_404(db, PendingPayment, pending_id, "Pending payment")
        if obj.retry_count >= obj.max_retries:
            raise HTTPException(
                status_code=400,
                detail=f"Maximum retries ({obj.max_retries}) exceeded",
            )
        obj.retry_count += 1
        obj.last_retry_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def download_pending_report(db: Session) -> str:

        rows = db.execute(
            select(PendingPayment)
            .where(PendingPayment.is_resolved == False)
            .order_by(PendingPayment.days_pending.desc())
        ).scalars().all()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            ["Employee Code", "Employee Name", "Bank", "Account",
             "Amount", "Failure Reason", "Error Code", "Retries", "Days Pending"]
        )
        for r in rows:
            writer.writerow(
                [r.employee_code or "", r.employee_name, r.bank_name, r.bank_account,
                 r.amount, r.failure_reason or "", r.error_code or "",
                 r.retry_count, r.days_pending]
            )
        return output.getvalue()


class PaymentSettingsService:

    @staticmethod
    def get(db: Session) -> PaymentSettings:
        obj = db.execute(select(PaymentSettings)).scalar_one_or_none()
        if not obj:

            obj = PaymentSettings()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    @staticmethod
    def upsert(db: Session, payload: PaymentSettingsUpsert) -> PaymentSettings:
        obj = db.execute(select(PaymentSettings)).scalar_one_or_none()
        if obj:
            for k, v in payload.model_dump(exclude_unset=True).items():
                setattr(obj, k, v)
            obj.updated_at = datetime.utcnow()
        else:
            obj = PaymentSettings(**payload.model_dump())
            db.add(obj)
        db.commit()
        db.refresh(obj)
        logger.info("PaymentSettings updated")
        return obj



class BankReconciliationService:

    @staticmethod
    def run_reconciliation(db: Session, payload: BankReconciliationCreate) -> BankReconciliation:

        session_obj = BankReconciliation(
            payment_file_id=payload.payment_file_id,
            payroll_run_id=payload.payroll_run_id,
            bank_name=payload.bank_name,
            total_amount=payload.total_amount,
            statement_file_name=payload.statement_file_name,
            statement_date=payload.statement_date,
            run_by=payload.run_by,
            notes=payload.notes,
        )
        db.add(session_obj)
        db.flush()

        if payload.payment_file_id:
            transfers = db.execute(
                select(BankTransfer).where(
                    BankTransfer.payment_file_id == payload.payment_file_id
                )
            ).scalars().all()

            matched = unmatched = pending = 0

            for i, t in enumerate(transfers, start=1):
               
                if t.status == TransferStatus.SUCCESS:
                    rec_status = ReconciliationStatus.MATCHED
                    matched += 1
                elif t.status == TransferStatus.FAILED:
                    rec_status = ReconciliationStatus.UNMATCHED
                    unmatched += 1
                else:
                    rec_status = ReconciliationStatus.PENDING
                    pending += 1

                entry = BankReconciliationEntry(
                    reconciliation_id=session_obj.id,
                    bank_transfer_id=t.id,
                    transaction_id=f"TXN{i:03d}",
                    reference_number=t.utr_number,
                    employee_id=t.employee_id,
                    employee_name=t.employee_name,
                    bank_name=t.bank_name,
                    bank_account=t.bank_account,
                    expected_amount=t.transfer_amount,
                    actual_amount=t.transfer_amount,
                    status=rec_status,
                    mismatch_reason=t.failure_reason if rec_status == ReconciliationStatus.UNMATCHED else None,
                )
                db.add(entry)

            total_count = matched + unmatched + pending
            session_obj.matched_count = matched
            session_obj.unmatched_count = unmatched
            session_obj.pending_count = pending
            session_obj.success_rate = (
                round((matched / total_count) * 100, 2) if total_count else Decimal("0")
            )

        db.commit()
        db.refresh(session_obj)
        logger.info(
            "Reconciliation run id=%s matched=%s unmatched=%s",
            session_obj.id, session_obj.matched_count, session_obj.unmatched_count,
        )
        return session_obj

    @staticmethod
    def get_by_id(db: Session, recon_id: int) -> BankReconciliation:
        return _get_or_404(db, BankReconciliation, recon_id, "Reconciliation")

    @staticmethod
    def list_all(
        db: Session,
        payment_file_id: Optional[int] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> Tuple[List[BankReconciliation], int]:
        stmt = select(BankReconciliation)
        if payment_file_id:
            stmt = stmt.where(BankReconciliation.payment_file_id == payment_file_id)
        total = db.execute(select(func.count()).select_from(stmt.subquery())).scalar_one()
        rows = db.execute(
            stmt.order_by(BankReconciliation.run_at.desc()).offset(skip).limit(limit)
        ).scalars().all()
        return rows, total

    @staticmethod
    def verify(db: Session, recon_id: int, verified_by: int, notes: Optional[str] = None) -> BankReconciliation:
        obj = _get_or_404(db, BankReconciliation, recon_id, "Reconciliation")
        if obj.is_verified:
            raise HTTPException(status_code=400, detail="Reconciliation already verified")
        obj.is_verified = True
        obj.verified_at = datetime.utcnow()
        obj.verified_by = verified_by
        if notes:
            obj.notes = notes
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def get_entries(db: Session, recon_id: int) -> List[BankReconciliationEntry]:
        return db.execute(
            select(BankReconciliationEntry)
            .where(BankReconciliationEntry.reconciliation_id == recon_id)
            .order_by(BankReconciliationEntry.id)
        ).scalars().all()

    @staticmethod
    def update_entry(
        db: Session, entry_id: int, payload: BankReconciliationEntryUpdate
    ) -> BankReconciliationEntry:
        obj = _get_or_404(db, BankReconciliationEntry, entry_id, "Reconciliation entry")
        for k, v in payload.model_dump(exclude_unset=True).items():
            setattr(obj, k, v)
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj

    @staticmethod
    def mark_all_verified(db: Session, recon_id: int) -> BankReconciliation:
        
        _get_or_404(db, BankReconciliation, recon_id, "Reconciliation")
        pending_entries = db.execute(
            select(BankReconciliationEntry).where(
                and_(
                    BankReconciliationEntry.reconciliation_id == recon_id,
                    BankReconciliationEntry.status == ReconciliationStatus.PENDING,
                )
            )
        ).scalars().all()

        for e in pending_entries:
            e.status = ReconciliationStatus.MATCHED
            e.updated_at = datetime.utcnow()

        obj = db.get(BankReconciliation, recon_id)
        obj.matched_count += len(pending_entries)
        obj.pending_count = 0
        total = obj.matched_count + obj.unmatched_count
        obj.success_rate = round((obj.matched_count / total) * 100, 2) if total else Decimal("0")
        obj.is_verified = True
        obj.verified_at = datetime.utcnow()
        obj.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(obj)
        return obj


class PaymentAnalyticsService:

    @staticmethod
    def get_dashboard_summary(db: Session) -> DashboardSummaryResponse:
        
        now = datetime.utcnow()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        total_processed = db.execute(
            select(func.coalesce(func.sum(BankTransfer.transfer_amount), 0)).where(
                BankTransfer.created_at >= month_start
            )
        ).scalar_one()

        def _count(stat: TransferStatus):
            return db.execute(
                select(func.count()).where(BankTransfer.status == stat)
            ).scalar_one()

        return DashboardSummaryResponse(
            total_processed=Decimal(str(total_processed)),
            successful_count=_count(TransferStatus.SUCCESS),
            pending_count=_count(TransferStatus.PENDING),
            failed_count=_count(TransferStatus.FAILED),
        )

    @staticmethod
    def get_analytics(db: Session, months: int = 4) -> PaymentAnalyticsResponse:
      
        total_amount = db.execute(
            select(func.coalesce(func.sum(BankTransfer.transfer_amount), 0))
        ).scalar_one()

        total_txns = db.execute(select(func.count(BankTransfer.id))).scalar_one()

        success_count = db.execute(
            select(func.count()).where(BankTransfer.status == TransferStatus.SUCCESS)
        ).scalar_one()

        success_rate = round((success_count / total_txns * 100), 1) if total_txns else 0.0

    
        monthly: List[MonthlyTrendItem] = []
        now = datetime.utcnow()
        for i in range(months - 1, -1, -1):

            target = now - timedelta(days=30 * i)
            m_start = target.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if m_start.month == 12:
                m_end = m_start.replace(year=m_start.year + 1, month=1)
            else:
                m_end = m_start.replace(month=m_start.month + 1)

            row_amount = db.execute(
                select(func.coalesce(func.sum(BankTransfer.transfer_amount), 0)).where(
                    and_(BankTransfer.transfer_date >= m_start, BankTransfer.transfer_date < m_end)
                )
            ).scalar_one()

            row_txns = db.execute(
                select(func.count()).where(
                    and_(BankTransfer.transfer_date >= m_start, BankTransfer.transfer_date < m_end)
                )
            ).scalar_one()

            row_success = db.execute(
                select(func.count()).where(
                    and_(
                        BankTransfer.transfer_date >= m_start,
                        BankTransfer.transfer_date < m_end,
                        BankTransfer.status == TransferStatus.SUCCESS,
                    )
                )
            ).scalar_one()

            monthly.append(
                MonthlyTrendItem(
                    month=m_start.strftime("%b %Y"),
                    amount=Decimal(str(row_amount)),
                    transactions=row_txns,
                    success_count=row_success,
                )
            )

        bank_rows = db.execute(
            select(BankTransfer.bank_name, func.sum(BankTransfer.transfer_amount).label("amt"))
            .group_by(BankTransfer.bank_name)
            .order_by(func.sum(BankTransfer.transfer_amount).desc())
        ).all()

        bank_dist = [
            BankDistributionItem(bank_name=r.bank_name, amount=Decimal(str(r.amt or 0)))
            for r in bank_rows
        ]


        pt_rows = db.execute(
            select(BankTransfer.payment_type, func.count(BankTransfer.id).label("cnt"))
            .group_by(BankTransfer.payment_type)
        ).all()

        pt_dist = [
            PaymentTypeDistributionItem(payment_type=r.payment_type, count=r.cnt)
            for r in pt_rows
        ]


        def _st_count(s: TransferStatus) -> int:
            return db.execute(
                select(func.count()).where(BankTransfer.status == s)
            ).scalar_one()

        status_summary = TransactionStatusSummary(
            processed=_st_count(TransferStatus.PROCESSED),
            failed=_st_count(TransferStatus.FAILED),
            pending=_st_count(TransferStatus.PENDING),
            generated=db.execute(
                select(func.count()).where(PaymentFile.status == PaymentFileStatus.GENERATED)
            ).scalar_one(),
        )

        return PaymentAnalyticsResponse(
            total_amount=Decimal(str(total_amount)),
            success_rate=success_rate,
            total_transactions=total_txns,
            avg_processing_time_hrs=2.4,  
            monthly_trends=monthly,
            bank_distribution=bank_dist,
            payment_type_distribution=pt_dist,
            transaction_status=status_summary,
        )
    