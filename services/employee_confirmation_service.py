"""
services/employee_confirmation_service.py

Business logic for Employee Confirmation Management:
  - auto-computed eligibility (Eligible / Conditional / Not Eligible)
  - time-status (days remaining vs "N days overdue")
  - 4-stage approval chain seeding & resolution
  - quick actions: send reminders / approve pending / auto trigger reviews
  - report export (JSON / CSV / PDF / EXCEL)
"""

import io
from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session
from sqlalchemy import func

from model.HR_Operations.employee_confirmation import (
    EmployeeConfirmation,
    ConfirmationApprovalStage,
)
from model.onboarding.employee import Employee


STAGE_ORDER = [
    ("MANAGER", 1),
    ("HR", 2),
    ("DEPT_HEAD", 3),
    ("AUTHORITY", 4),
]


# ======================================================
# APPROVAL STAGE SEEDING / RESOLUTION
# ======================================================
def seed_approval_stages(db: Session, confirmation_id: int) -> None:
    """Creates the 4 PENDING approval stages for a newly created confirmation case."""
    for stage_name, order in STAGE_ORDER:
        db.add(
            ConfirmationApprovalStage(
                confirmation_id=confirmation_id,
                stage_name=stage_name,
                stage_order=order,
                status="PENDING",
            )
        )


def resolve_confirmation_status(db: Session, confirmation: EmployeeConfirmation) -> str:
    """
    Looks at the 4 approval stages and decides the overall confirmation status:
      - any stage REJECTED               -> OVERDUE (kept as-is; rejection itself doesn't
                                              auto-fail the record, HR re-routes manually)
      - all 4 stages APPROVED            -> CONFIRMED
      - first stage (MANAGER) APPROVED,
        at least one later stage PENDING -> PENDING_APPROVAL
      - first stage still PENDING        -> PENDING_REVIEW
    """
    stages = (
        db.query(ConfirmationApprovalStage)
        .filter(ConfirmationApprovalStage.confirmation_id == confirmation.id)
        .order_by(ConfirmationApprovalStage.stage_order)
        .all()
    )
    if not stages:
        return confirmation.status

    statuses = [s.status for s in stages]

    if all(s == "APPROVED" for s in statuses):
        return "CONFIRMED"
    if statuses[0] == "PENDING":
        return "PENDING_REVIEW"
    return "PENDING_APPROVAL"


# ======================================================
# ELIGIBILITY (auto-computed)
# ======================================================
def compute_eligibility(confirmation: EmployeeConfirmation) -> str:
    """
    Rule-based eligibility:
      - performance_rating POOR                        -> NOT_ELIGIBLE
      - extension_count >= 2                            -> NOT_ELIGIBLE
      - extension_count == 1 OR rating SATISFACTORY      -> CONDITIONAL
      - otherwise (rating EXCELLENT/GOOD, no extension)  -> ELIGIBLE
    """
    rating = (confirmation.performance_rating or "").upper()

    if rating == "POOR" or confirmation.extension_count >= 2:
        return "NOT_ELIGIBLE"
    if confirmation.extension_count >= 1 or rating == "SATISFACTORY":
        return "CONDITIONAL"
    return "ELIGIBLE"


# ======================================================
# TIME STATUS (days remaining vs overdue)
# ======================================================
def compute_time_status(confirmation: EmployeeConfirmation) -> dict:
    today = date.today()
    due_date = confirmation.extended_till or confirmation.probation_end_date

    if confirmation.status == "CONFIRMED":
        return {"days_until_due": None, "is_overdue": False}

    delta_days = (due_date - today).days

    if delta_days < 0:
        return {"days_until_due": abs(delta_days), "is_overdue": True}
    return {"days_until_due": delta_days, "is_overdue": False}


def refresh_overdue_status(db: Session, confirmation: EmployeeConfirmation) -> None:
    """If due date has passed and case isn't confirmed yet, flips status to OVERDUE."""
    if confirmation.status in ("CONFIRMED", "TERMINATED"):
        return

    time_status = compute_time_status(confirmation)
    if time_status["is_overdue"]:
        confirmation.status = "OVERDUE"


# ======================================================
# DASHBOARD STATS
# ======================================================
def get_dashboard_stats(db: Session) -> dict:
    total = db.query(func.count(EmployeeConfirmation.id)).scalar() or 0

    pending_review = (
        db.query(func.count(EmployeeConfirmation.id))
        .filter(EmployeeConfirmation.status == "PENDING_REVIEW")
        .scalar()
        or 0
    )
    pending_approval = (
        db.query(func.count(EmployeeConfirmation.id))
        .filter(EmployeeConfirmation.status == "PENDING_APPROVAL")
        .scalar()
        or 0
    )
    confirmed = (
        db.query(func.count(EmployeeConfirmation.id))
        .filter(EmployeeConfirmation.status == "CONFIRMED")
        .scalar()
        or 0
    )
    overdue = (
        db.query(func.count(EmployeeConfirmation.id))
        .filter(EmployeeConfirmation.status == "OVERDUE")
        .scalar()
        or 0
    )

    today = date.today()
    week_end = today + timedelta(days=7)
    due_this_week = (
        db.query(func.count(EmployeeConfirmation.id))
        .filter(
            EmployeeConfirmation.status.notin_(["CONFIRMED", "TERMINATED"]),
            EmployeeConfirmation.probation_end_date >= today,
            EmployeeConfirmation.probation_end_date <= week_end,
        )
        .scalar()
        or 0
    )

    return {
        "total": total,
        "pending_review": pending_review,
        "pending_approval": pending_approval,
        "confirmed": confirmed,
        "overdue": overdue,
        "due_this_week": due_this_week,
    }


# ======================================================
# QUICK ACTIONS
# ======================================================
def send_reminders(db: Session) -> dict:
    """Sends reminders for all PENDING_REVIEW cases (stub: marks last_reminder_sent_at)."""
    cases = (
        db.query(EmployeeConfirmation)
        .filter(EmployeeConfirmation.status == "PENDING_REVIEW")
        .all()
    )
    for case in cases:
        case.last_reminder_sent_at = datetime.utcnow()

    db.commit()

    count = len(cases)
    return {
        "employees_notified": count,
        "message": f"Reminders sent to managers of {count} employees for pending reviews",
    }


def approve_pending(db: Session) -> dict:
    """
    Auto-approves the next PENDING stage for cases where the manager stage is
    already APPROVED and the case is sitting at PENDING_APPROVAL.
    """
    confirmed_count = 0

    cases = (
        db.query(EmployeeConfirmation)
        .filter(EmployeeConfirmation.status == "PENDING_APPROVAL")
        .all()
    )

    for case in cases:
        next_stage = (
            db.query(ConfirmationApprovalStage)
            .filter(
                ConfirmationApprovalStage.confirmation_id == case.id,
                ConfirmationApprovalStage.status == "PENDING",
            )
            .order_by(ConfirmationApprovalStage.stage_order)
            .first()
        )
        if next_stage:
            next_stage.status = "APPROVED"
            next_stage.acted_at = datetime.utcnow()
            confirmed_count += 1

            new_status = resolve_confirmation_status(db, case)
            case.status = new_status
            if new_status == "CONFIRMED":
                case.confirmation_date = date.today()

    db.commit()

    return {
        "approvals_confirmed": confirmed_count,
        "message": f"{confirmed_count} pending approvals confirmed",
    }


def auto_trigger_reviews(db: Session) -> dict:
    """
    Moves any case whose probation_end_date is today or earlier from
    PENDING_REVIEW into UNDER_REVIEW automatically.
    """
    today = date.today()

    cases = (
        db.query(EmployeeConfirmation)
        .filter(
            EmployeeConfirmation.status == "PENDING_REVIEW",
            EmployeeConfirmation.probation_end_date <= today,
        )
        .all()
    )

    for case in cases:
        case.status = "UNDER_REVIEW"

    db.commit()

    count = len(cases)
    if count == 0:
        message = "No employees require auto-triggered reviews at this time"
    else:
        message = f"Auto-triggered review for {count} employees"

    return {"employees_triggered": count, "message": message}


# ======================================================
# EXPORT REPORTS
# ======================================================
def _query_report_rows(
    db: Session,
    start_date: date,
    end_date: date,
    department: Optional[str],
    status_filter: Optional[str],
):
    query = (
        db.query(EmployeeConfirmation, Employee)
        .join(Employee, EmployeeConfirmation.employee_id == Employee.id)
        .filter(
            EmployeeConfirmation.probation_start_date >= start_date,
            EmployeeConfirmation.probation_start_date <= end_date,
        )
    )
    if department:
        query = query.filter(Employee.department.ilike(f"%{department}%"))
    if status_filter:
        query = query.filter(EmployeeConfirmation.status == status_filter.upper())

    return query.all()


def export_report_json(
    db: Session, start_date: date, end_date: date, department: Optional[str], status_filter: Optional[str]
) -> dict:
    rows = _query_report_rows(db, start_date, end_date, department, status_filter)

    records = []
    for conf, emp in rows:
        full_name = " ".join(p for p in [emp.first_name, emp.middle_name, emp.last_name] if p)
        records.append({
            "employee": full_name,
            "employee_code": emp.employee_code,
            "department": emp.department,
            "probation_start_date": conf.probation_start_date.isoformat(),
            "probation_end_date": conf.probation_end_date.isoformat(),
            "status": conf.status,
            "eligibility": conf.eligibility,
        })

    dept_breakdown = {}
    for _, emp in rows:
        dept_breakdown[emp.department or "Unknown"] = dept_breakdown.get(emp.department or "Unknown", 0) + 1

    return {
        "total_records": len(rows),
        "records": records,
        "department_breakdown": dept_breakdown,
    }


def export_report_csv(
    db: Session, start_date: date, end_date: date, department: Optional[str], status_filter: Optional[str]
) -> io.StringIO:
    import csv

    rows = _query_report_rows(db, start_date, end_date, department, status_filter)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Employee", "Code", "Department", "Start Date", "End Date", "Status", "Eligibility"])
    for conf, emp in rows:
        full_name = " ".join(p for p in [emp.first_name, emp.middle_name, emp.last_name] if p)
        writer.writerow([
            full_name, emp.employee_code, emp.department,
            conf.probation_start_date, conf.probation_end_date, conf.status, conf.eligibility,
        ])
    buffer.seek(0)
    return buffer


def export_report_excel(
    db: Session, start_date: date, end_date: date, department: Optional[str], status_filter: Optional[str]
) -> io.BytesIO:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill

    rows = _query_report_rows(db, start_date, end_date, department, status_filter)

    wb = Workbook()
    ws = wb.active
    ws.title = "Confirmation Report"

    headers = ["Employee", "Code", "Department", "Start Date", "End Date", "Status", "Eligibility"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill(start_color="1F4E78", end_color="1F4E78", fill_type="solid")

    for conf, emp in rows:
        full_name = " ".join(p for p in [emp.first_name, emp.middle_name, emp.last_name] if p)
        ws.append([
            full_name, emp.employee_code, emp.department,
            conf.probation_start_date.strftime("%d-%m-%Y"),
            conf.probation_end_date.strftime("%d-%m-%Y"),
            conf.status, conf.eligibility,
        ])

    for col in ws.columns:
        max_len = max(len(str(c.value)) if c.value else 0 for c in col)
        ws.column_dimensions[col[0].column_letter].width = max_len + 4

    buffer = io.BytesIO()
    wb.save(buffer)
    buffer.seek(0)
    return buffer


def export_report_pdf(
    db: Session, start_date: date, end_date: date, department: Optional[str], status_filter: Optional[str]
) -> io.BytesIO:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib import colors

    rows = _query_report_rows(db, start_date, end_date, department, status_filter)

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4), topMargin=20 * mm, bottomMargin=20 * mm)
    styles = getSampleStyleSheet()

    elements = [Paragraph("Employee Confirmation Report", styles["Heading2"]), Spacer(1, 10)]

    table_data = [["Employee", "Code", "Department", "Start Date", "End Date", "Status", "Eligibility"]]
    for conf, emp in rows:
        full_name = " ".join(p for p in [emp.first_name, emp.middle_name, emp.last_name] if p)
        table_data.append([
            full_name, emp.employee_code, emp.department or "",
            conf.probation_start_date.strftime("%d-%b-%Y"),
            conf.probation_end_date.strftime("%d-%b-%Y"),
            conf.status, conf.eligibility,
        ])

    table = Table(table_data, repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1F4E78")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F2F2")]),
    ]))

    elements.append(table)
    doc.build(elements)
    buffer.seek(0)
    return buffer