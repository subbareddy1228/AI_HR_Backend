"""
services/regularization_service.py
Business logic for Regularization Workflow module — all 4 tabs.
"""

import csv, io, logging
from datetime import date, datetime, timezone, timedelta
from typing import Optional, List

from sqlalchemy.orm import Session
from sqlalchemy import func, or_

from model.HR_Automation.regularization import (
    RegularizationRequest, AutoRejectRule, BulkRegularizationProcess,
    RegularizationReport, RequestTypeEnum, RequestStatusEnum,
    IssueTypeEnum, ReportFormatEnum,
)

logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────
# DEFAULT AUTO-REJECT RULES (matches component's initialState)
# ─────────────────────────────────────────────────────────

DEFAULT_AUTO_REJECT_RULES = [
    {"request_type": "missing", "days": 7, "enabled": True},
    {"request_type": "forgot",  "days": 5, "enabled": True},
]

REQUEST_TYPE_LABELS = {
    "missing":   "Missing Punch",
    "incorrect": "Incorrect Time",
    "forgot":    "Forgot Punch",
    "wfh":       "WFH Regularization",
    "on_duty":   "On-Duty",
}


# ─────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────

def _resolve_employee(db: Session, employee_id: str) -> dict:
    try:
        from model.onboarding.employee import Employee
        emp = db.query(Employee).filter_by(employee_id=employee_id).first()
        if emp:
            return {
                "name":       emp.name,
                "department": getattr(emp, "department", ""),
            }
    except ImportError:
        pass
    return {"name": employee_id, "department": ""}


def _display_datetime(req: RegularizationRequest) -> str:
    """Build the Date/Time column string from type-specific fields."""
    if req.request_type == RequestTypeEnum.missing and req.date_time:
        return req.date_time.strftime("%Y-%m-%d %H:%M")
    if req.request_type == RequestTypeEnum.incorrect and req.original_time:
        return req.original_time.strftime("%Y-%m-%d %H:%M")
    if req.request_type == RequestTypeEnum.forgot and req.punch_date:
        return str(req.punch_date)
    if req.request_type == RequestTypeEnum.wfh and req.wfh_date:
        return str(req.wfh_date)
    if req.request_type == RequestTypeEnum.on_duty and req.od_date:
        return f"{req.od_date} {req.from_time or ''}–{req.to_time or ''}"
    return "N/A"


def _build_req_out(db: Session, req: RegularizationRequest) -> dict:
    emp = _resolve_employee(db, req.employee_id)
    return {
        "id":               req.id,
        "employee_id":      req.employee_id,
        "employeeName":     emp["name"],
        "department":       emp["department"],
        "requestType":      req.request_type,
        "status":           req.status,
        "dateTime":         req.date_time,
        "originalTime":     req.original_time,
        "correctedTime":    req.corrected_time,
        "date":             req.punch_date or req.wfh_date or req.od_date,
        "punchType":        req.punch_type,
        "approxTime":       req.approx_time,
        "location":         req.location,
        "workSummary":      req.work_summary,
        "fromTime":         req.from_time,
        "toTime":           req.to_time,
        "dutyType":         req.duty_type,
        "purpose":          req.purpose,
        "reason":           req.reason,
        "remarks":          req.remarks,
        "attachments":      req.attachments or [],
        "approvalWorkflow": req.approval_workflow or [],
        "approvedAt":       req.approved_at,
        "rejectedAt":       req.rejected_at,
        "rejectionReason":  req.rejection_reason,
        "isAutoRejected":   req.is_auto_rejected,
        "submittedAt":      req.submitted_at,
        "submittedBy":      req.submitted_by,
        "displayDateTime":  _display_datetime(req),
    }


def _build_rule_out(rule: AutoRejectRule) -> dict:
    return {
        "id":               rule.id,
        "requestType":      rule.request_type,
        "days":             rule.days,
        "enabled":          rule.enabled,
        "updated_at":       rule.updated_at,
        "requestTypeLabel": REQUEST_TYPE_LABELS.get(rule.request_type.value, rule.request_type.value),
        "daysDisplay":      f"{rule.days} days",
        "statusDisplay":    "Enabled" if rule.enabled else "Disabled",
    }


# ═══════════════════════════════════════════════════════════
# STARTUP SEED
# ═══════════════════════════════════════════════════════════

def seed_auto_reject_rules(db: Session):
    """Called once at startup — inserts default rules if table is empty."""
    if db.query(AutoRejectRule).count() > 0:
        return
    for data in DEFAULT_AUTO_REJECT_RULES:
        db.add(AutoRejectRule(**data))
    db.commit()
    logger.info("Seeded %d default auto-reject rules.", len(DEFAULT_AUTO_REJECT_RULES))


# ═══════════════════════════════════════════════════════════
# TAB 1 — REQUEST SERVICE
# ═══════════════════════════════════════════════════════════

class RegularizationRequestService:

    @staticmethod
    def list(
        db: Session,
        search: Optional[str]             = None,
        status: Optional[RequestStatusEnum] = None,
        request_type: Optional[RequestTypeEnum] = None,
        page:     int = 1,
        page_size:int = 20,
    ) -> dict:
        q = db.query(RegularizationRequest)

        if status:
            q = q.filter_by(status=status)
        if request_type:
            q = q.filter_by(request_type=request_type)
        if search:
            # Search by employee name or reason (join Employee for name search)
            term = f"%{search.lower()}%"
            try:
                from model.onboarding.employee import Employee
                q = q.join(Employee,
                            Employee.employee_id == RegularizationRequest.employee_id,
                            isouter=True)
                q = q.filter(
                    or_(
                        func.lower(Employee.name).like(term),
                        func.lower(RegularizationRequest.reason).like(term),
                    )
                )
            except ImportError:
                q = q.filter(func.lower(RegularizationRequest.reason).like(term))

        total = q.count()
        items = (
            q.order_by(RegularizationRequest.submitted_at.desc())
             .offset((page - 1) * page_size)
             .limit(page_size)
             .all()
        )
        return {
            "total":     total,
            "page":      page,
            "page_size": page_size,
            "items":     [_build_req_out(db, r) for r in items],
        }

    @staticmethod
    def get(db: Session, request_id: int) -> dict:
        req = db.query(RegularizationRequest).filter_by(id=request_id).first()
        if not req:
            raise ValueError(f"Request {request_id} not found.")
        return _build_req_out(db, req)

    @staticmethod
    def create(
        db:         Session,
        payload,
        created_by: Optional[int] = None,
        attachment_path: Optional[str] = None,
    ) -> dict:
        emp = _resolve_employee(db, payload.employeeId)

        # Build approval workflow from request type
        workflow = [
            {"level": 1, "approver": "Manager", "status": "pending", "required": True},
            {"level": 2, "approver": "HR",       "status": "pending", "required": True},
        ]

        req = RegularizationRequest(
            employee_id=payload.employeeId,
            request_type=payload.requestType,
            status=RequestStatusEnum.pending,
            # Type-specific
            date_time=payload.dateTime,
            original_time=payload.originalTime,
            corrected_time=payload.correctedTime,
            punch_date=payload.date if payload.requestType == "forgot" else None,
            wfh_date=payload.date  if payload.requestType == "wfh"    else None,
            od_date=payload.date   if payload.requestType == "on_duty" else None,
            punch_type=payload.punchType,
            approx_time=payload.approxTime,
            location=payload.location,
            work_summary=payload.summary,
            from_time=payload.fromTime,
            to_time=payload.toTime,
            duty_type=payload.dutyType,
            purpose=payload.purpose,
            # Common
            reason=payload.reason,
            remarks=payload.remarks,
            attachment_path=attachment_path,
            attachments=[attachment_path] if attachment_path else [],
            approval_workflow=workflow,
            submitted_by=emp["name"],
            created_by=created_by,
        )
        db.add(req)
        db.commit()
        db.refresh(req)
        logger.info("Regularization request created: %s %s", payload.employeeId, payload.requestType)
        return _build_req_out(db, req)

    @staticmethod
    def decide(
        db:          Session,
        request_id:  int,
        action:      str,
        remarks:     str,
        decided_by:  Optional[int] = None,
        decided_by_name: str = "Manager",
    ) -> dict:
        req = db.query(RegularizationRequest).filter_by(id=request_id).first()
        if not req:
            raise ValueError(f"Request {request_id} not found.")
        if req.status != RequestStatusEnum.pending:
            raise ValueError("Only pending requests can be decided.")

        now = datetime.now(timezone.utc)

        if action == "approve":
            req.status      = RequestStatusEnum.approved
            req.approved_at = now
            req.approved_by = decided_by
            # Update workflow steps
            req.approval_workflow = [
                {**step, "status": "approved"} for step in (req.approval_workflow or [])
            ]
        elif action == "reject":
            req.status           = RequestStatusEnum.rejected
            req.rejected_at      = now
            req.rejected_by      = decided_by
            req.rejection_reason = remarks or "Not approved."
            req.approval_workflow = [
                {**step, "status": "rejected"} for step in (req.approval_workflow or [])
            ]
        else:
            # request_changes — stays pending, add remark to workflow
            req.approval_workflow = [
                {**step, "remarks": remarks} if step.get("status") == "pending" else step
                for step in (req.approval_workflow or [])
            ]

        db.commit()
        db.refresh(req)
        logger.info("Request %d %s by %s", request_id, action, decided_by_name)
        return _build_req_out(db, req)

    @staticmethod
    def delete(db: Session, request_id: int) -> None:
        req = db.query(RegularizationRequest).filter_by(id=request_id).first()
        if not req:
            raise ValueError(f"Request {request_id} not found.")
        db.delete(req)
        db.commit()


# ═══════════════════════════════════════════════════════════
# AUTO-REJECT CRON JOB
# ═══════════════════════════════════════════════════════════

class AutoRejectService:
    """
    Mirrors the component's useEffect auto-reject logic.
    Called by a scheduled cron job (APScheduler / Celery beat) every hour.
    """

    @staticmethod
    def run(db: Session) -> int:
        rules = {r.request_type: r for r in
                 db.query(AutoRejectRule).filter_by(enabled=True).all()}
        today   = datetime.now(timezone.utc)
        count   = 0

        pending = db.query(RegularizationRequest).filter_by(
            status=RequestStatusEnum.pending
        ).all()

        for req in pending:
            rule = rules.get(req.request_type)
            if not rule:
                continue
            days_diff = (today - req.submitted_at).days
            if days_diff >= rule.days:
                req.status           = RequestStatusEnum.auto_rejected
                req.rejected_at      = today
                req.rejection_reason = f"Auto-rejected after {rule.days} days"
                req.is_auto_rejected = True
                count += 1

        if count:
            db.commit()
            logger.info("Auto-rejected %d request(s).", count)
        return count


# ═══════════════════════════════════════════════════════════
# TAB 2 — SETTINGS SERVICE
# ═══════════════════════════════════════════════════════════

class SettingsService:

    @staticmethod
    def list_rules(db: Session) -> List[dict]:
        rules = db.query(AutoRejectRule).order_by(AutoRejectRule.id).all()
        return [_build_rule_out(r) for r in rules]

    @staticmethod
    def toggle_rule(
        db: Session, rule_id: int, updated_by: Optional[int] = None
    ) -> dict:
        rule = db.query(AutoRejectRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Rule {rule_id} not found.")
        rule.enabled    = not rule.enabled
        rule.updated_by = updated_by
        db.commit()
        db.refresh(rule)
        return _build_rule_out(rule)

    @staticmethod
    def update_rule(
        db: Session, rule_id: int, payload, updated_by: Optional[int] = None
    ) -> dict:
        rule = db.query(AutoRejectRule).filter_by(id=rule_id).first()
        if not rule:
            raise ValueError(f"Rule {rule_id} not found.")
        if payload.days is not None:
            rule.days = payload.days
        if payload.enabled is not None:
            rule.enabled = payload.enabled
        rule.updated_by = updated_by
        db.commit()
        db.refresh(rule)
        return _build_rule_out(rule)

    @staticmethod
    def get_statistics(db: Session) -> dict:
        """Request Statistics — right panel of Settings tab."""
        total    = db.query(RegularizationRequest).count()
        pending  = db.query(RegularizationRequest).filter_by(status="pending").count()
        approved = db.query(RegularizationRequest).filter_by(status="approved").count()
        rejected = db.query(RegularizationRequest).filter(
            RegularizationRequest.status.in_(["rejected", "auto-rejected"])
        ).count()
        return {
            "totalRequests": total,
            "pending":       pending,
            "approved":      approved,
            "rejected":      rejected,
        }


# ═══════════════════════════════════════════════════════════
# TAB 3 — BULK PROCESSING SERVICE
# ═══════════════════════════════════════════════════════════

class BulkProcessingService:

    @staticmethod
    def list(db: Session) -> List[BulkRegularizationProcess]:
        return db.query(BulkRegularizationProcess) \
                  .order_by(BulkRegularizationProcess.processed_at.desc()).all()

    @staticmethod
    def process(
        db:           Session,
        payload,
        file_path:    Optional[str] = None,
        processed_by: Optional[int] = None,
        processed_by_name: str = "HR Admin",
    ) -> BulkRegularizationProcess:
        """
        Process Bulk modal → Process Bulk button.
        1. Identifies affected employees (from file or all active)
        2. Creates approved RegularizationRequests for each
        3. Stores the batch record
        """
        # Resolve employee list
        emp_ids = list(payload.employeeIds)
        if not emp_ids:
            try:
                from model.onboarding.employee import Employee
                emp_ids = [
                    e.employee_id
                    for e in db.query(Employee).filter_by(status="Active").all()
                ]
            except ImportError:
                pass

        count = len(emp_ids)

        # Auto-create approved requests for each employee
        for emp_id in emp_ids:
            emp = _resolve_employee(db, emp_id)
            db.add(RegularizationRequest(
                employee_id=emp_id,
                request_type=RequestTypeEnum.missing,
                status=RequestStatusEnum.approved,
                reason=f"Bulk regularization — {payload.issueType.value} issue "
                       f"from {payload.fromDate} to {payload.toDate}",
                remarks="Auto-processed via bulk regularization",
                submitted_by=emp["name"],
                approved_at=datetime.now(timezone.utc),
                approval_workflow=[
                    {"level": 1, "approver": "HR Admin",
                     "status": "approved", "required": True}
                ],
            ))

        batch = BulkRegularizationProcess(
            from_date=payload.fromDate,
            to_date=payload.toDate,
            issue_type=payload.issueType,
            employee_ids=emp_ids,
            file_path=file_path,
            processed_count=count,
            status="completed",
            processed_by=processed_by,
            processed_by_name=processed_by_name,
        )
        db.add(batch)
        db.commit()
        db.refresh(batch)
        logger.info("Bulk process: %d employees, %s issue, %s–%s",
                    count, payload.issueType, payload.fromDate, payload.toDate)
        return batch


# ═══════════════════════════════════════════════════════════
# TAB 4 — REPORTS SERVICE
# ═══════════════════════════════════════════════════════════

class ReportsService:

    @staticmethod
    def list(db: Session) -> List[RegularizationReport]:
        return db.query(RegularizationReport) \
                  .order_by(RegularizationReport.generated_at.desc()).all()

    @staticmethod
    def generate(
        db:               Session,
        payload,
        generated_by:     Optional[int] = None,
        generated_by_name:str = "HR Admin",
    ) -> tuple[RegularizationReport, bytes]:
        """
        Reports tab → Generate Report button.
        Filters requests by date range + type, builds summary, returns CSV bytes.
        """
        q = db.query(RegularizationRequest).filter(
            RegularizationRequest.submitted_at >= datetime.combine(
                payload.fromDate, datetime.min.time()
            ).replace(tzinfo=timezone.utc),
            RegularizationRequest.submitted_at <= datetime.combine(
                payload.toDate, datetime.max.time()
            ).replace(tzinfo=timezone.utc),
        )
        if payload.requestType:
            q = q.filter_by(request_type=payload.requestType)

        requests = q.order_by(RegularizationRequest.submitted_at.desc()).all()

        # Build summary
        summary = {
            "totalRequests": len(requests),
            "pending":  sum(1 for r in requests if r.status == "pending"),
            "approved": sum(1 for r in requests if r.status == "approved"),
            "rejected": sum(1 for r in requests if r.status in ("rejected", "auto-rejected")),
            "byType":   {},
            "byDepartment": {},
        }
        for r in requests:
            summary["byType"][r.request_type.value] = \
                summary["byType"].get(r.request_type.value, 0) + 1
            emp = _resolve_employee(db, r.employee_id)
            dept = emp["department"] or "Unknown"
            summary["byDepartment"][dept] = summary["byDepartment"].get(dept, 0) + 1

        # Generate CSV bytes
        csv_bytes = ReportsService._to_csv(db, requests)

        # Filename
        ts        = datetime.now(timezone.utc)
        fmt       = payload.format.value
        file_name = f"regularization-report-{int(ts.timestamp())}.{fmt}"

        report = RegularizationReport(
            from_date=payload.fromDate,
            to_date=payload.toDate,
            request_type=payload.requestType,
            format=payload.format,
            file_name=file_name,
            total_records=len(requests),
            summary=summary,
            generated_by=generated_by,
            generated_by_name=generated_by_name,
        )
        db.add(report)
        db.commit()
        db.refresh(report)
        return report, csv_bytes

    @staticmethod
    def _to_csv(db: Session, requests: list) -> bytes:
        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Employee", "Department", "Request Type",
            "Date/Time", "Reason", "Status", "Submitted At",
        ])
        for r in requests:
            emp = _resolve_employee(db, r.employee_id)
            writer.writerow([
                r.id, emp["name"], emp["department"],
                REQUEST_TYPE_LABELS.get(r.request_type.value, r.request_type.value),
                _display_datetime(r), r.reason, r.status,
                r.submitted_at.strftime("%Y-%m-%d %H:%M"),
            ])
        return output.getvalue().encode("utf-8")
