"""
services/leave_management_service.py
All business logic for Leave Management System — all 7 tabs.
Mirrors exact logic from the 3280-line LeaveManagement.jsx component.
"""

import calendar as cal_lib
import csv, io, logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, or_, distinct

from model.HR_Automation.leave_management import (
    LeaveType, LeaveBalance, LeaveAdjustment,
    LeaveApplication, CompOff, LeavePlanningCampaign, ApprovalDelegation,
    AccrualTypeEnum, ApplicationStatusEnum, AdjustmentTypeEnum,
    CompOffStatusEnum, CompOffPolicyEnum,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# DEFAULT LEAVE TYPES  (from initialLeaveTypes in component)
# ─────────────────────────────────────────────────────────

DEFAULT_LEAVE_TYPES = [
    {"name": "Casual Leave",     "code": "CL", "is_paid": True,
     "accrual_type": "monthly",  "accrual_amount": 1.5, "max_accrual": 12,
     "carry_forward_enabled": True,  "carry_forward_max_days": 3,  "carry_forward_expiry_months": 3,
     "encashment_enabled": True,     "encashment_max_days": 5,     "encashment_rate": 1.0,
     "allow_half_day": True,  "allow_short_leave": True,
     "description": "Casual leave for personal work"},
    {"name": "Sick Leave",       "code": "SL", "is_paid": True,
     "accrual_type": "monthly",  "accrual_amount": 1.0, "max_accrual": 12,
     "carry_forward_enabled": True,  "carry_forward_max_days": 5,  "carry_forward_expiry_months": 6,
     "encashment_enabled": False,    "encashment_max_days": 0,     "encashment_rate": 0,
     "allow_half_day": False, "probation_applicable": True, "allow_backdated": True,
     "description": "Medical leave with certificate requirement"},
    {"name": "Earned Leave",     "code": "EL", "is_paid": True,
     "accrual_type": "monthly",  "accrual_amount": 1.25,"max_accrual": 15,
     "carry_forward_enabled": True,  "carry_forward_max_days": 10, "carry_forward_expiry_months": 12,
     "encashment_enabled": True,     "encashment_max_days": 10,    "encashment_rate": 1.0,
     "allow_half_day": True,
     "description": "Earned leave with encashment option"},
    {"name": "Maternity Leave",  "code": "ML", "is_paid": True,
     "accrual_type": "on-joining", "accrual_amount": 26.0,"max_accrual": 26,
     "carry_forward_enabled": False, "encashment_enabled": False,
     "allow_half_day": False, "usage_limit": 1,
     "description": "Maternity leave for female employees"},
    {"name": "Paternity Leave",  "code": "PL", "is_paid": True,
     "accrual_type": "on-joining", "accrual_amount": 5.0, "max_accrual": 5,
     "carry_forward_enabled": False, "encashment_enabled": False,
     "allow_half_day": False, "usage_limit": 1,
     "description": "Paternity leave for male employees"},
    {"name": "Bereavement Leave","code": "BL", "is_paid": True,
     "accrual_type": "annual",    "accrual_amount": 3.0, "max_accrual": 3,
     "carry_forward_enabled": False, "encashment_enabled": False,
     "allow_half_day": False, "probation_applicable": True, "allow_backdated": True,
     "description": "Leave for family bereavement"},
]


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _resolve_employee(db, employee_id: str) -> dict:
    try:
        from model.onboarding.employee import Employee
        emp = db.query(Employee).filter_by(employee_id=employee_id).first()
        if emp:
            return {
                "name":       emp.name,
                "department": getattr(emp, "department", ""),
                "position":   getattr(emp, "position", ""),
            }
    except ImportError:
        pass
    return {"name": employee_id, "department": "", "position": ""}


def _get_or_create_balance(db: Session, employee_id: str, leave_type_id: int, year: int) -> LeaveBalance:
    bal = db.query(LeaveBalance).filter_by(
        employee_id=employee_id, leave_type_id=leave_type_id, year=year
    ).first()
    if not bal:
        bal = LeaveBalance(employee_id=employee_id, leave_type_id=leave_type_id, year=year)
        db.add(bal)
        db.flush()
    return bal


def _accrual_display(lt: LeaveType) -> str:
    unit = "month" if lt.accrual_type == AccrualTypeEnum.monthly else "year"
    amt  = int(lt.accrual_amount) if lt.accrual_amount == int(lt.accrual_amount) else lt.accrual_amount
    return f"{amt}/{unit}"


def _cf_display(lt: LeaveType) -> str:
    if lt.carry_forward_enabled and lt.carry_forward_max_days > 0:
        return f"{lt.carry_forward_max_days} days ({lt.carry_forward_expiry_months}M)"
    return "No"


def _enc_display(lt: LeaveType) -> str:
    if lt.encashment_enabled and lt.encashment_max_days > 0:
        rate = int(lt.encashment_rate) if lt.encashment_rate == int(lt.encashment_rate) else lt.encashment_rate
        return f"{lt.encashment_max_days} days @ {rate}x"
    return "No"


def _build_lt_out(lt: LeaveType) -> dict:
    return {
        "id": lt.id, "name": lt.name, "code": lt.code,
        "description": lt.description, "isPaid": lt.is_paid, "isActive": lt.is_active,
        "accrualType": lt.accrual_type, "accrualAmount": lt.accrual_amount,
        "maxAccrual": lt.max_accrual,
        "carryForward": {"enabled": lt.carry_forward_enabled,
                         "maxDays": lt.carry_forward_max_days,
                         "expiryMonths": lt.carry_forward_expiry_months},
        "encashment": {"enabled": lt.encashment_enabled,
                       "maxDays": lt.encashment_max_days,
                       "rate": lt.encashment_rate},
        "allowHalfDay": lt.allow_half_day, "allowNegative": lt.allow_negative,
        "probationApplicable": lt.probation_applicable, "sandwichLeave": lt.sandwich_leave,
        "allowBackdated": lt.allow_backdated, "allowShortLeave": lt.allow_short_leave,
        "isOptional": lt.is_optional, "usageLimit": lt.usage_limit,
        "proration": lt.proration or {"enabled": True, "method": "proportional"},
        "approvalWorkflow": lt.approval_workflow or {"levels": 1, "approvers": []},
        "accrualDisplay": _accrual_display(lt),
        "carryForwardDisplay": _cf_display(lt),
        "encashmentDisplay": _enc_display(lt),
        "halfDayDisplay": "Yes" if lt.allow_half_day else "No",
        "paidDisplay": "Paid" if lt.is_paid else "Unpaid",
        "statusDisplay": "Active" if lt.is_active else "Inactive",
        "created_at": lt.created_at,
    }


# ══════════════════════════════════════════════════════════
# TAB 1 — LEAVE TYPE SERVICE
# ══════════════════════════════════════════════════════════

class LeaveTypeService:

    @staticmethod
    def seed(db: Session):
        """Called once from Alembic data migration or startup event — NOT on every request."""
        if db.query(LeaveType).count() == 0:
            for d in DEFAULT_LEAVE_TYPES:
                db.add(LeaveType(**{k: v for k, v in d.items()
                                    if hasattr(LeaveType, k)}))
            db.commit()

    @staticmethod
    def list(db: Session, active_only: bool = False) -> List[dict]:
        q = db.query(LeaveType)
        if active_only:
            q = q.filter_by(is_active=True)
        return [_build_lt_out(lt) for lt in q.order_by(LeaveType.id).all()]

    @staticmethod
    def get(db: Session, lt_id: int) -> LeaveType:
        lt = db.query(LeaveType).filter_by(id=lt_id).first()
        if not lt:
            raise ValueError(f"Leave type {lt_id} not found.")
        return lt

    @staticmethod
    def create(db: Session, payload, created_by=None) -> dict:
        if db.query(LeaveType).filter_by(code=payload.code).first():
            raise ValueError(f"Code '{payload.code}' already exists.")
        lt = LeaveType(
            name=payload.name, code=payload.code, description=payload.description,
            is_paid=payload.isPaid, accrual_type=payload.accrualType,
            accrual_amount=payload.accrualAmount, max_accrual=payload.maxAccrual,
            carry_forward_enabled=payload.carryForward.enabled,
            carry_forward_max_days=payload.carryForward.maxDays,
            carry_forward_expiry_months=payload.carryForward.expiryMonths,
            encashment_enabled=payload.encashment.enabled,
            encashment_max_days=payload.encashment.maxDays,
            encashment_rate=payload.encashment.rate,
            allow_half_day=payload.allowHalfDay, allow_negative=payload.allowNegative,
            probation_applicable=payload.probationApplicable, sandwich_leave=payload.sandwichLeave,
            allow_backdated=payload.allowBackdated, allow_short_leave=payload.allowShortLeave,
            is_optional=payload.isOptional, usage_limit=payload.usageLimit,
            proration=payload.proration.model_dump(),
            approval_workflow=payload.approvalWorkflow.model_dump(),
            created_by=created_by,
        )
        db.add(lt)
        db.commit()
        db.refresh(lt)
        return _build_lt_out(lt)

    @staticmethod
    def update(db: Session, lt_id: int, payload, updated_by=None) -> dict:
        lt = LeaveTypeService.get(db, lt_id)
        field_map = {
            "isPaid": "is_paid", "accrualType": "accrual_type", "accrualAmount": "accrual_amount",
            "maxAccrual": "max_accrual", "allowHalfDay": "allow_half_day",
            "allowNegative": "allow_negative", "probationApplicable": "probation_applicable",
            "sandwichLeave": "sandwich_leave", "allowBackdated": "allow_backdated",
            "allowShortLeave": "allow_short_leave", "isOptional": "is_optional",
            "usageLimit": "usage_limit", "isActive": "is_active",
            "name": "name", "description": "description",
        }
        for py_name, db_name in field_map.items():
            val = getattr(payload, py_name, None)
            if val is not None:
                setattr(lt, db_name, val)
        if payload.carryForward:
            lt.carry_forward_enabled       = payload.carryForward.enabled
            lt.carry_forward_max_days      = payload.carryForward.maxDays
            lt.carry_forward_expiry_months = payload.carryForward.expiryMonths
        if payload.encashment:
            lt.encashment_enabled  = payload.encashment.enabled
            lt.encashment_max_days = payload.encashment.maxDays
            lt.encashment_rate     = payload.encashment.rate
        if payload.proration:
            lt.proration = payload.proration.model_dump()
        if payload.approvalWorkflow:
            lt.approval_workflow = payload.approvalWorkflow.model_dump()
        db.commit()
        db.refresh(lt)
        return _build_lt_out(lt)

    @staticmethod
    def delete(db: Session, lt_id: int):
        lt = LeaveTypeService.get(db, lt_id)
        pending = db.query(LeaveApplication).filter_by(
            leave_type_id=lt_id, status=ApplicationStatusEnum.pending
        ).count()
        if pending:
            raise ValueError(f"Cannot delete — {pending} pending applications exist.")
        lt.is_active = False
        db.commit()


# ══════════════════════════════════════════════════════════
# TAB 2 — LEAVE BALANCE SERVICE
# ══════════════════════════════════════════════════════════

class LeaveBalanceService:

    @staticmethod
    def list(db: Session, employee_id=None, leave_type_id=None, year=None) -> List[dict]:
        year = year or date.today().year
        q = db.query(LeaveBalance).filter_by(year=year)
        if employee_id: q = q.filter_by(employee_id=employee_id)
        if leave_type_id: q = q.filter_by(leave_type_id=leave_type_id)
        result = []
        for b in q.all():
            emp  = _resolve_employee(db, b.employee_id)
            lt   = b.leave_type
            # Projected balance — remaining months × accrual rate
            today = date.today()
            months_left = 12 - today.month
            projected = b.balance
            if lt and lt.accrual_type == AccrualTypeEnum.monthly:
                projected = min(b.balance + lt.accrual_amount * months_left, lt.max_accrual)
            result.append({
                "id": b.id, "employee_id": b.employee_id, "employeeName": emp["name"],
                "leave_type_id": b.leave_type_id, "leaveTypeName": lt.name if lt else "",
                "leaveTypeCode": lt.code if lt else "", "year": b.year,
                "openingBalance": b.opening_balance, "accrued": b.accrued,
                "carryForward": b.carry_forward, "used": b.used, "encashed": b.encashed,
                "balance": b.balance, "projectedBalance": round(projected, 1),
                "lastAccrualDate": b.last_accrual_date,
            })
        return result

    @staticmethod
    def adjust(db: Session, payload, approved_by=None) -> LeaveBalance:
        year = payload.effectiveDate.year
        bal  = _get_or_create_balance(db, payload.employeeId, payload.leaveTypeId, year)
        if payload.openingBalance > 0:
            bal.opening_balance = payload.openingBalance
        if payload.adjustmentType == AdjustmentTypeEnum.credit:
            bal.accrued  += payload.adjustmentAmount
            bal.balance  += payload.adjustmentAmount
        else:
            bal.used    += payload.adjustmentAmount
            bal.balance -= payload.adjustmentAmount
        db.add(LeaveAdjustment(
            employee_id=payload.employeeId, leave_type_id=payload.leaveTypeId,
            adjustment_type=payload.adjustmentType, amount=payload.adjustmentAmount,
            reason=payload.reason, effective_date=payload.effectiveDate, approved_by=approved_by,
        ))
        db.commit()
        db.refresh(bal)
        return bal

    @staticmethod
    def run_auto_accrual(db: Session) -> dict:
        """Auto Accrual button — credits monthly accruals for all active employees."""
        try:
            from model.onboarding.employee import Employee
            employees = db.query(Employee).filter_by(status="Active").all()
        except ImportError:
            return {"processed": 0, "skipped": 0, "message": "Employee model not found."}

        leave_types = db.query(LeaveType).filter_by(
            is_active=True, accrual_type=AccrualTypeEnum.monthly
        ).all()

        year = date.today().year
        processed, skipped = 0, 0
        for emp in employees:
            for lt in leave_types:
                if lt.probation_applicable:
                    join = getattr(emp, "date_of_joining", None)
                    if join and (date.today() - join).days < 90:
                        skipped += 1
                        continue
                bal = _get_or_create_balance(db, emp.employee_id, lt.id, year)
                new_accrued = min(bal.accrued + lt.accrual_amount, lt.max_accrual)
                credited    = new_accrued - bal.accrued
                if credited > 0:
                    bal.accrued += credited
                    bal.balance += credited
                    bal.last_accrual_date = datetime.now(timezone.utc)
                    processed += 1
                else:
                    skipped += 1
        db.commit()
        return {"processed": processed, "skipped": skipped,
                "message": f"Accrual complete — {processed} credited, {skipped} skipped."}

    @staticmethod
    def process_lapse(db: Session) -> dict:
        """Process Lapse button — expires carry-forward leaves past their expiry date."""
        today   = date.today()
        lapsed  = 0
        for bal in db.query(LeaveBalance).filter(LeaveBalance.carry_forward > 0).all():
            lt = bal.leave_type
            if not lt or not lt.carry_forward_enabled:
                continue
            if bal.last_carry_forward_date:
                expiry = bal.last_carry_forward_date.date()
                expiry = expiry.replace(
                    month=((expiry.month - 1 + lt.carry_forward_expiry_months) % 12) + 1,
                    year=expiry.year + (expiry.month - 1 + lt.carry_forward_expiry_months) // 12,
                )
                if expiry < today:
                    bal.balance      -= bal.carry_forward
                    bal.carry_forward = 0
                    lapsed += 1
        db.commit()
        return {"lapsed": lapsed, "message": f"Processed {lapsed} lapsed leave(s)."}

    @staticmethod
    def export_statement(db: Session, employee_id: Optional[str], year: int) -> bytes:
        q = db.query(LeaveBalance).filter_by(year=year)
        if employee_id:
            q = q.filter_by(employee_id=employee_id)
        rows = q.all()
        out  = io.StringIO()
        w    = csv.writer(out)
        w.writerow(["Employee","Leave Type","Opening","Accrued","Used","Carry Fwd","Encashed","Balance"])
        for b in rows:
            emp = _resolve_employee(db, b.employee_id)
            lt  = b.leave_type
            w.writerow([emp["name"], lt.name if lt else "", b.opening_balance, b.accrued,
                        b.used, b.carry_forward, b.encashed, b.balance])
        return out.getvalue().encode("utf-8")


# ══════════════════════════════════════════════════════════
# TAB 3 — APPLICATION SERVICE
# ══════════════════════════════════════════════════════════

class LeaveApplicationService:

    @staticmethod
    def check_overlap(db: Session, employee_id: str, start_date: date, end_date: date) -> dict:
        overlaps = db.query(LeaveApplication).filter(
            LeaveApplication.employee_id == employee_id,
            LeaveApplication.status.in_([ApplicationStatusEnum.pending,
                                          ApplicationStatusEnum.approved]),
            LeaveApplication.start_date <= end_date,
            or_(LeaveApplication.end_date >= start_date, LeaveApplication.end_date.is_(None)),
        ).all()
        return {"employeeId": employee_id, "hasOverlap": bool(overlaps), "overlapping": overlaps}

    @staticmethod
    def _get_effective_approver(db: Session, role: str, app_date: date) -> str:
        delegation = db.query(ApprovalDelegation).filter(
            ApprovalDelegation.from_approver == role,
            ApprovalDelegation.start_date    <= app_date,
            ApprovalDelegation.end_date      >= app_date,
            ApprovalDelegation.is_active     == True,
        ).first()
        return delegation.to_approver if delegation else role

    @staticmethod
    def apply(db: Session, payload, applied_by_user=None) -> List[LeaveApplication]:
        leave_type = None
        if payload.leaveTypeId:
            leave_type = db.query(LeaveType).filter_by(id=payload.leaveTypeId, is_active=True).first()
            if not leave_type:
                raise ValueError("Leave type not found or inactive.")

        end_date = payload.endDate or payload.startDate
        days     = 0.5 if payload.halfDay else max(1.0, (end_date - payload.startDate).days + 1)

        emp_ids = payload.bulkEmployees if payload.isBulk else [payload.employeeId]
        created = []

        for emp_id in emp_ids:
            # Balance check
            current_balance = 0.0
            if leave_type:
                bal = db.query(LeaveBalance).filter_by(
                    employee_id=emp_id, leave_type_id=leave_type.id, year=payload.startDate.year
                ).first()
                current_balance = bal.balance if bal else 0.0
                if not leave_type.allow_negative and current_balance < days:
                    raise ValueError(f"Insufficient {leave_type.name} balance for {emp_id}.")
                if leave_type.usage_limit:
                    used_count = db.query(LeaveApplication).filter(
                        LeaveApplication.employee_id == emp_id,
                        LeaveApplication.leave_type_id == leave_type.id,
                        LeaveApplication.status == ApplicationStatusEnum.approved,
                        func.extract("year", LeaveApplication.start_date) == payload.startDate.year,
                    ).count()
                    if used_count >= leave_type.usage_limit:
                        raise ValueError(f"Usage limit reached for {leave_type.name}.")

            # Auto-approve if ≤ 1 day (matches component logic)
            auto_approve = days <= 1

            # Build approval workflow
            wf = []
            if leave_type and leave_type.approval_workflow:
                for a in leave_type.approval_workflow.get("approvers", []):
                    effective = LeaveApplicationService._get_effective_approver(
                        db, a["role"], payload.startDate
                    )
                    wf.append({
                        "level": a["level"], "approver": effective,
                        "originalApprover": a["role"],
                        "status": "approved" if auto_approve else "pending",
                        "required": a.get("required", True),
                        "delegated": effective != a["role"],
                    })

            emp_info = _resolve_employee(db, emp_id)
            app = LeaveApplication(
                employee_id=emp_id, leave_type_id=payload.leaveTypeId,
                leave_type_name=leave_type.name if leave_type else "Comp-Off",
                start_date=payload.startDate, end_date=end_date, days=days,
                half_day=payload.halfDay, half_day_type=payload.halfDayType,
                reason=payload.reason, is_bulk=payload.isBulk,
                bulk_employee_ids=emp_ids if payload.isBulk else [],
                applied_by=emp_info["name"], current_balance=current_balance,
                status=ApplicationStatusEnum.approved if auto_approve else ApplicationStatusEnum.pending,
                is_auto_approved=auto_approve, approval_workflow=wf,
            )
            db.add(app)
            db.flush()

            # Deduct balance
            if leave_type and auto_approve:
                bal = _get_or_create_balance(db, emp_id, leave_type.id, payload.startDate.year)
                bal.used    += days
                bal.balance -= days

            created.append(app)

        db.commit()
        for a in created: db.refresh(a)
        return created

    @staticmethod
    def list(db: Session, employee_id=None, status=None, search=None, page=1, page_size=20) -> dict:
        q = db.query(LeaveApplication)
        if employee_id: q = q.filter_by(employee_id=employee_id)
        if status:      q = q.filter_by(status=status)
        if search:
            term = f"%{search.lower()}%"
            q = q.filter(
                func.lower(LeaveApplication.applied_by).like(term) |
                func.lower(LeaveApplication.leave_type_name).like(term)
            )
        total = q.count()
        apps  = q.order_by(LeaveApplication.applied_at.desc()) \
                  .offset((page-1)*page_size).limit(page_size).all()
        items = []
        for a in apps:
            emp = _resolve_employee(db, a.employee_id)
            row = {c.name: getattr(a, c.name) for c in a.__table__.columns}
            row["employeeName"] = emp["name"]
            # camelCase aliases
            row["leaveTypeName"]    = a.leave_type_name
            row["isCompOff"]        = a.is_comp_off
            row["startDate"]        = a.start_date
            row["endDate"]          = a.end_date
            row["halfDay"]          = a.half_day
            row["halfDayType"]      = a.half_day_type
            row["attachmentPath"]   = a.attachment_path
            row["isAutoApproved"]   = a.is_auto_approved
            row["isBulk"]           = a.is_bulk
            row["appliedAt"]        = a.applied_at
            row["appliedBy"]        = a.applied_by
            row["currentBalance"]   = a.current_balance
            row["approvedAt"]       = a.approved_at
            row["rejectionReason"]  = a.rejection_reason
            row["withdrawnAt"]      = a.withdrawn_at
            row["approvalWorkflow"] = a.approval_workflow
            items.append(row)
        return {"total": total, "page": page, "page_size": page_size, "items": items}

    @staticmethod
    def decide(db: Session, app_id: int, approved: bool, rejection_reason: str, decided_by) -> LeaveApplication:
        app = db.query(LeaveApplication).filter_by(id=app_id).first()
        if not app: raise ValueError(f"Application {app_id} not found.")
        if app.status != ApplicationStatusEnum.pending:
            raise ValueError("Application already processed.")
        now = datetime.now(timezone.utc)
        if approved:
            app.status      = ApplicationStatusEnum.approved
            app.approved_at = now
            app.approved_by = decided_by
            # Deduct balance
            if app.leave_type_id:
                bal = db.query(LeaveBalance).filter_by(
                    employee_id=app.employee_id, leave_type_id=app.leave_type_id,
                    year=app.start_date.year
                ).first()
                if bal:
                    bal.used    += app.days
                    bal.balance -= app.days
        else:
            app.status           = ApplicationStatusEnum.rejected
            app.rejected_at      = now
            app.rejection_reason = rejection_reason or "Not approved."
        db.commit()
        db.refresh(app)
        return app

    @staticmethod
    def withdraw(db: Session, app_id: int) -> LeaveApplication:
        app = db.query(LeaveApplication).filter_by(id=app_id).first()
        if not app: raise ValueError(f"Application {app_id} not found.")
        if app.status not in (ApplicationStatusEnum.pending, ApplicationStatusEnum.approved):
            raise ValueError("Only pending or approved applications can be withdrawn.")
        app.status       = ApplicationStatusEnum.withdrawn
        app.withdrawn_at = datetime.now(timezone.utc)
        if app.leave_type_id:
            bal = db.query(LeaveBalance).filter_by(
                employee_id=app.employee_id, leave_type_id=app.leave_type_id,
                year=app.start_date.year
            ).first()
            if bal:
                bal.used    -= app.days
                bal.balance += app.days
        db.commit()
        db.refresh(app)
        return app


# ══════════════════════════════════════════════════════════
# TAB 4 — CALENDAR SERVICE
# ══════════════════════════════════════════════════════════

class LeaveCalendarService:

    @staticmethod
    def get_month(db: Session, year: int, month: int, department: Optional[str] = None) -> dict:
        _, days_in_month = cal_lib.monthrange(year, month)
        start = date(year, month, 1)
        end   = date(year, month, days_in_month)
        apps  = db.query(LeaveApplication).filter(
            LeaveApplication.status == ApplicationStatusEnum.approved,
            LeaveApplication.start_date <= end,
            or_(LeaveApplication.end_date >= start, LeaveApplication.end_date.is_(None)),
        ).all()

        day_map: dict[int, list] = {d: [] for d in range(1, days_in_month + 1)}
        dept_map: dict = {}

        for app in apps:
            emp = _resolve_employee(db, app.employee_id)
            if department and emp["department"] != department: continue
            s = max(app.start_date, start)
            e = min(app.end_date or app.start_date, end)
            cur = s
            while cur <= e:
                day_map[cur.day].append({
                    "employeeId": app.employee_id, "name": emp["name"],
                    "leaveTypeName": app.leave_type_name, "status": app.status,
                })
                dept = emp["department"]
                dept_map.setdefault(dept, {"count": 0, "employees": set()})
                dept_map[dept]["count"] += 1
                dept_map[dept]["employees"].add(app.employee_id)
                cur += timedelta(days=1)

        month_labels = ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"]
        return {
            "year": year, "month": month,
            "monthLabel": f"{month_labels[month-1]}-{year}",
            "days": [
                {"day": d, "date": date(year, month, d),
                 "leaves": day_map[d], "hasOverlap": len(day_map[d]) > 3}
                for d in range(1, days_in_month + 1)
            ],
            "deptStats": [
                {"department": dept, "employeeCount": len(v["employees"]), "daysCount": v["count"]}
                for dept, v in dept_map.items()
            ],
        }


# ══════════════════════════════════════════════════════════
# TAB 5 — COMP-OFF SERVICE
# ══════════════════════════════════════════════════════════

class CompOffService:

    @staticmethod
    def list(db: Session, employee_id=None, status=None) -> List[dict]:
        q = db.query(CompOff)
        if employee_id: q = q.filter_by(employee_id=employee_id)
        if status:      q = q.filter_by(status=status)
        today  = date.today()
        result = []
        for c in q.order_by(CompOff.earned_date.desc()).all():
            is_expired = bool(c.expiry_date and c.expiry_date < today)
            if is_expired and c.status == CompOffStatusEnum.available:
                c.status = CompOffStatusEnum.expired
                db.commit()
            emp = _resolve_employee(db, c.employee_id)
            result.append({
                "id": c.id, "employee_id": c.employee_id, "employeeName": emp["name"],
                "earnedDate": c.earned_date, "hours": c.hours, "days": round(c.hours / 8, 2),
                "expiryDate": c.expiry_date, "source": c.source, "policyType": c.policy_type,
                "description": c.description, "status": c.status, "applied": c.applied,
                "isExpired": is_expired, "created_at": c.created_at,
            })
        return result

    @staticmethod
    def create(db: Session, payload, created_by=None) -> CompOff:
        co = CompOff(
            employee_id=payload.employeeId, earned_date=payload.earnedDate,
            hours=payload.hours, expiry_date=payload.expiryDate,
            source=payload.source, policy_type=payload.policyType,
            description=payload.description, created_by=created_by,
        )
        db.add(co)
        db.flush()
        if co.policy_type == CompOffPolicyEnum.compOff:
            lt = db.query(LeaveType).filter_by(code="CO").first()
            if lt:
                bal = _get_or_create_balance(db, co.employee_id, lt.id, co.earned_date.year)
                bal.accrued += round(co.hours / 8, 2)
                bal.balance += round(co.hours / 8, 2)
        db.commit()
        db.refresh(co)
        return co

    @staticmethod
    def apply_comp_off(db: Session, comp_off_id: int) -> LeaveApplication:
        co = db.query(CompOff).filter_by(id=comp_off_id).first()
        if not co: raise ValueError(f"Comp-off {comp_off_id} not found.")
        if co.status != CompOffStatusEnum.available or co.applied:
            raise ValueError("Comp-off already applied or not available.")
        today = date.today()
        app = LeaveApplication(
            employee_id=co.employee_id, leave_type_id=None,
            leave_type_name="Comp-Off", is_comp_off=True, comp_off_id=co.id,
            start_date=today, end_date=today, days=round(co.hours / 8, 2),
            reason=f"Comp-off application for {co.hours} hours", status=ApplicationStatusEnum.pending,
            applied_by=co.employee_id,
        )
        db.add(app)
        co.applied = True
        co.status  = CompOffStatusEnum.applied
        db.commit()
        db.refresh(app)
        return app


# ══════════════════════════════════════════════════════════
# TAB 6 — PLANNING SERVICE
# ══════════════════════════════════════════════════════════

class LeavePlanningService:

    @staticmethod
    def coverage(db: Session, start_date: date, end_date: date, department: Optional[str] = None) -> List[dict]:
        try:
            from model.onboarding.employee import Employee
            q = db.query(Employee).filter_by(status="Active")
            all_employees = q.all()
        except ImportError:
            return []

        departments = (
            [department] if department and department != "All"
            else sorted(set(getattr(e, "department", "Unknown") for e in all_employees))
        )

        apps = db.query(LeaveApplication).filter(
            LeaveApplication.status == ApplicationStatusEnum.approved,
            LeaveApplication.start_date <= end_date,
            or_(LeaveApplication.end_date >= start_date, LeaveApplication.end_date.is_(None)),
        ).all()

        result = []
        for dept in departments:
            dept_emps = [e for e in all_employees if getattr(e, "department", "") == dept]
            on_leave  = len(set(
                a.employee_id for a in apps
                if _resolve_employee(db, a.employee_id)["department"] == dept
            ))
            total     = len(dept_emps)
            coverage  = round((total - on_leave) / total * 100, 1) if total else 0.0
            result.append({
                "department": dept, "totalEmployees": total,
                "employeesOnLeave": on_leave, "coverage": str(coverage),
            })
        return result

    @staticmethod
    def list_campaigns(db: Session) -> List[LeavePlanningCampaign]:
        return db.query(LeavePlanningCampaign).order_by(
            LeavePlanningCampaign.created_at.desc()
        ).all()

    @staticmethod
    def create_campaign(db: Session, payload, created_by=None) -> LeavePlanningCampaign:
        camp = LeavePlanningCampaign(
            name=payload.name, period=payload.period,
            start_date=payload.startDate, end_date=payload.endDate,
            target_department=payload.targetDepartment,
            message=payload.message, status=payload.status, created_by=created_by,
        )
        db.add(camp)
        db.commit()
        db.refresh(camp)
        return camp


# ══════════════════════════════════════════════════════════
# TAB 7 — DELEGATION SERVICE
# ══════════════════════════════════════════════════════════

class DelegationService:

    @staticmethod
    def list(db: Session) -> List[dict]:
        today = date.today()
        result = []
        for d in db.query(ApprovalDelegation).order_by(ApprovalDelegation.start_date.desc()).all():
            result.append({
                "id": d.id, "fromApprover": d.from_approver, "toApprover": d.to_approver,
                "startDate": d.start_date, "endDate": d.end_date,
                "reason": d.reason, "isActive": d.is_active,
                "isCurrentlyActive": d.is_active and d.start_date <= today <= d.end_date,
                "created_at": d.created_at,
            })
        return result

    @staticmethod
    def create(db: Session, payload, created_by=None) -> ApprovalDelegation:
        d = ApprovalDelegation(
            from_approver=payload.fromApprover, to_approver=payload.toApprover,
            start_date=payload.startDate, end_date=payload.endDate,
            reason=payload.reason, is_active=True, created_by=created_by,
        )
        db.add(d)
        db.commit()
        db.refresh(d)
        return d

    @staticmethod
    def deactivate(db: Session, delegation_id: int) -> ApprovalDelegation:
        d = db.query(ApprovalDelegation).filter_by(id=delegation_id).first()
        if not d: raise ValueError(f"Delegation {delegation_id} not found.")
        d.is_active = False
        db.commit()
        return d
