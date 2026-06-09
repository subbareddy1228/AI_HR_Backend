# # services/Payroll/payroll_service.py
# Service layer for PayrollRun and PayrollRunDetail
# Also contains: PDF generation, email dispatch, bulk ZIP download
# (merged here to avoid adding new service files)

import io
import zipfile
import calendar
from typing import Optional, List
from decimal import Decimal

from fastapi import HTTPException, status
from fastapi_mail import FastMail, MessageSchema, MessageType
from sqlalchemy import select
from sqlalchemy.orm import Session

from core.mail import mail_config
from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from model.Payroll.salary_slip import SalarySlip, SalarySlipComponent
from model.Payroll.slip_distribution import SlipDistributionLog, SlipSettings
from schema.Payroll.payroll_run import (
    PayrollRunCreate, PayrollRunUpdate, PayrollRunDetailCreate,
)

MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"
]


# ─────────────────────────────────────────────────────────────────────────────
# ORIGINAL — PayrollRun CRUD  (unchanged)
# ─────────────────────────────────────────────────────────────────────────────

def create_payroll_run(db: Session, payload: PayrollRunCreate) -> PayrollRun:
    """Create a new payroll run with Draft status."""
    obj = PayrollRun(**payload.model_dump())
    obj.status = "Draft"
    db.add(obj)
    db.commit()
    db.refresh(obj)
    return obj


def list_payroll_runs(
    db: Session,
    year: Optional[int] = None,
    run_status: Optional[str] = None,
) -> List[PayrollRun]:
    """List payroll runs with optional year and status filters."""
    stmt = select(PayrollRun)
    if year:
        stmt = stmt.where(PayrollRun.run_year == year)
    if run_status:
        stmt = stmt.where(PayrollRun.status == run_status)
    return db.execute(stmt).scalars().all()


def get_payroll_run(db: Session, run_id: int) -> PayrollRun:
    """Fetch a single payroll run. Raises 404 if not found."""
    obj = db.execute(
        select(PayrollRun).where(PayrollRun.id == run_id)
    ).scalar_one_or_none()
    if not obj:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Payroll run not found",
        )
    return obj


def approve_payroll_run(
    db: Session, run_id: int, approved_by: Optional[str] = None
) -> PayrollRun:
    """Set payroll run status to Approved."""
    obj = get_payroll_run(db, run_id)
    obj.status = "Approved"
    if approved_by:
        obj.approved_by = approved_by
    db.commit()
    db.refresh(obj)
    return obj


def mark_payroll_run_paid(db: Session, run_id: int) -> PayrollRun:
    """Set payroll run status to Paid."""
    obj = get_payroll_run(db, run_id)
    obj.status = "Paid"
    db.commit()
    db.refresh(obj)
    return obj


def add_employee_to_run(
    db: Session, run_id: int, payload: PayrollRunDetailCreate
) -> PayrollRunDetail:
    """Add an employee entry to a payroll run and update run totals."""
    run = get_payroll_run(db, run_id)
    data = payload.model_dump()
    data["payroll_run_id"] = run_id
    detail = PayrollRunDetail(**data)
    db.add(detail)

    run.total_employees  = (run.total_employees or 0) + 1
    run.total_gross      = (run.total_gross or 0) + float(payload.gross_salary)
    run.total_deductions = (run.total_deductions or 0) + float(payload.total_deductions)
    run.total_net_pay    = (run.total_net_pay or 0) + float(payload.net_pay)

    db.commit()
    db.refresh(detail)
    return detail


def list_run_details(db: Session, run_id: int) -> List[PayrollRunDetail]:
    """List all employee details for a given payroll run."""
    get_payroll_run(db, run_id)
    return db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run_id)
    ).scalars().all()


# ─────────────────────────────────────────────────────────────────────────────
# PDF GENERATION  (merged from slip_pdf_service.py)
# ─────────────────────────────────────────────────────────────────────────────

def _fmt_inr(amount) -> str:
    """Format a number as Indian Rupee string."""
    try:
        val = int(Decimal(str(amount)))
        s = str(val)
        if len(s) <= 3:
            return f"₹{s}"
        last3 = s[-3:]
        rest  = s[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        if rest:
            groups.append(rest)
        groups.reverse()
        return f"₹{','.join(groups)},{last3}"
    except Exception:
        return f"₹{amount}"


def generate_pdf_bytes(
    slip_data: dict,
    components: list,
    company_name: str = "Company",
    company_address: str = "",
    signatory_name: str = "HR Manager",
    footer_text: str = "This is a system-generated salary slip.",
    confidentiality_note: str = "This document is confidential.",
) -> bytes:
    """
    Generate a styled salary slip PDF using ReportLab.

    slip_data  : dict with slip fields (employee_name, net_pay, etc.)
    components : list of dicts with keys component_type, component_name, amount
    Returns    : raw PDF bytes
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import mm
        from reportlab.lib.enums import TA_CENTER, TA_RIGHT
        from reportlab.platypus import (
            SimpleDocTemplate, Paragraph, Table, TableStyle, Spacer
        )
    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="reportlab is not installed. Run: pip install reportlab",
        )

    HEADER_BG  = colors.HexColor("#1E3A5F")
    SECTION_BG = colors.HexColor("#EBF2FA")
    BORDER_CLR = colors.HexColor("#B0C4D8")
    GREEN_NET  = colors.HexColor("#1B6B35")

    buffer = io.BytesIO()
    doc    = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=15*mm, bottomMargin=15*mm,
        leftMargin=20*mm, rightMargin=20*mm,
    )
    styles = getSampleStyleSheet()
    story  = []

    def para(text, align=None, size=9, color="#1A1A2E"):
        ps = ParagraphStyle(
            "p", parent=styles["Normal"], fontSize=size,
            textColor=colors.HexColor(color),
            alignment={"center": 1, "right": 2}.get(align, 0),
        )
        return Paragraph(text, ps)

    # Header
    hdr = Table([[
        para(f"<b>{company_name}</b><br/>"
             f"<font size='8' color='#B8D4F0'>{company_address}</font>",
             size=12, color="#FFFFFF"),
        para(f"<b>SALARY SLIP</b><br/>"
             f"<font size='9' color='#B8D4F0'>"
             f"{MONTH_NAMES[slip_data['slip_month']]} {slip_data['slip_year']}</font>",
             align="right", size=13, color="#FFFFFF"),
    ]], colWidths=[110*mm, 60*mm])
    hdr.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), HEADER_BG),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 10),
        ("BOTTOMPADDING", (0,0), (-1,-1), 10),
        ("VALIGN",        (0,0), (-1,-1), "MIDDLE"),
    ]))
    story += [hdr, Spacer(1, 6*mm)]

    # Employee details block
    def detail_row(label, value):
        return [
            para(f"<font color='#555566'>{label}</font>", size=8),
            para(f"<b>{value or '—'}</b>"),
        ]

    emp_rows_raw = [
        detail_row("Employee Name",  slip_data.get("employee_name", "")),
        detail_row("Employee Code",  slip_data.get("employee_code", "")),
        detail_row("Department",     slip_data.get("department", "")),
        detail_row("Designation",    slip_data.get("designation", "")),
        detail_row("PAN Number",     slip_data.get("pan_number", "")),
        detail_row("UAN Number",     slip_data.get("uan_number", "")),
        detail_row("Bank Account",   slip_data.get("bank_account", "")),
        detail_row("Bank Name",      slip_data.get("bank_name", "")),
    ]
    grid = []
    for i in range(0, len(emp_rows_raw), 2):
        r1 = emp_rows_raw[i]
        r2 = emp_rows_raw[i+1] if i+1 < len(emp_rows_raw) else [para(""), para("")]
        grid.append(r1 + [para("")] + r2)

    emp_t = Table(grid, colWidths=[35*mm, 45*mm, 5*mm, 35*mm, 50*mm])
    emp_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), SECTION_BG),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
        ("LINEBELOW",     (0,0), (-1,-2), 0.3, BORDER_CLR),
    ]))
    story += [para("<b>EMPLOYEE DETAILS</b>", size=9, color="#1E3A5F"),
              Spacer(1, 2*mm), emp_t, Spacer(1, 4*mm)]

    # Attendance
    att = Table([[
        para("<font color='#555566'>Days in Month</font>", size=8),
        para(f"<b>{slip_data.get('days_in_month', 30)}</b>"),
        para("<font color='#555566'>Days Worked</font>",  size=8),
        para(f"<b>{slip_data.get('days_worked', 0)}</b>"),
        para("<font color='#555566'>Days Absent</font>",  size=8),
        para(f"<b>{slip_data.get('days_absent', 0)}</b>"),
        para("<font color='#555566'>LOP Days</font>",     size=8),
        para(f"<b>{slip_data.get('lop_days', 0)}</b>"),
    ]], colWidths=[28*mm, 15*mm, 28*mm, 15*mm, 28*mm, 15*mm, 20*mm, 21*mm])
    att.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), SECTION_BG),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
    ]))
    story += [para("<b>ATTENDANCE</b>", size=9, color="#1E3A5F"),
              Spacer(1, 2*mm), att, Spacer(1, 4*mm)]

    # Earnings & Deductions
    earnings   = [c for c in components if (c.get("component_type") if isinstance(c, dict) else c.component_type) == "earning"]
    deductions = [c for c in components if (c.get("component_type") if isinstance(c, dict) else c.component_type) == "deduction"]

    def gf(c, f):
        return c.get(f) if isinstance(c, dict) else getattr(c, f)

    comp_rows = [[
        para("<b>EARNINGS</b>",   color="#FFFFFF"),
        para("<b>AMOUNT</b>",  align="right", color="#FFFFFF"),
        para("<b>DEDUCTIONS</b>", color="#FFFFFF"),
        para("<b>AMOUNT</b>",  align="right", color="#FFFFFF"),
    ]]
    for i in range(max(len(earnings), len(deductions))):
        e = earnings[i]   if i < len(earnings)   else None
        d = deductions[i] if i < len(deductions) else None
        comp_rows.append([
            para(gf(e, "component_name") if e else ""),
            para(_fmt_inr(gf(e, "amount")) if e else "", align="right"),
            para(gf(d, "component_name") if d else ""),
            para(_fmt_inr(gf(d, "amount")) if d else "", align="right"),
        ])
    comp_rows.append([
        para("<b>Gross Earnings</b>"),
        para(f"<b>{_fmt_inr(slip_data.get('total_earnings', 0))}</b>", align="right"),
        para("<b>Total Deductions</b>"),
        para(f"<b>{_fmt_inr(slip_data.get('total_deductions', 0))}</b>", align="right"),
    ])

    comp_t = Table(comp_rows, colWidths=[60*mm, 25*mm, 60*mm, 25*mm])
    comp_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0), HEADER_BG),
        ("BACKGROUND",    (0,-1), (-1,-1), SECTION_BG),
        ("LINEBELOW",     (0,0), (-1,-2), 0.3, BORDER_CLR),
        ("LINEABOVE",     (0,-1), (-1,-1), 0.8, BORDER_CLR),
        ("LINEAFTER",     (1,0), (1,-1), 0.5, BORDER_CLR),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("RIGHTPADDING",  (0,0), (-1,-1), 6),
        ("TOPPADDING",    (0,0), (-1,-1), 4),
        ("BOTTOMPADDING", (0,0), (-1,-1), 4),
    ]))
    story += [para("<b>EARNINGS & DEDUCTIONS</b>", size=9, color="#1E3A5F"),
              Spacer(1, 2*mm), comp_t, Spacer(1, 5*mm)]

    # Net Pay
    net_t = Table([[
        para("NET PAY (Take Home)", color="#FFFFFF", size=10),
        para(f"<b>{_fmt_inr(slip_data.get('net_pay', 0))}</b>",
             align="right", color="#FFFFFF", size=14),
    ]], colWidths=[110*mm, 60*mm])
    net_t.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,-1), GREEN_NET),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("RIGHTPADDING",  (0,0), (-1,-1), 8),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
    ]))
    story += [net_t, Spacer(1, 10*mm)]

    # Signatory + footer
    sig_t = Table([[
        para(confidentiality_note, size=8, color="#555566"),
        para(f"<b>{signatory_name}</b><br/>"
             f"<font size='8' color='#555566'>Authorised Signatory</font>",
             align="right"),
    ]], colWidths=[100*mm, 70*mm])
    sig_t.setStyle(TableStyle([
        ("LINEABOVE", (0,0), (-1,0), 0.5, BORDER_CLR),
        ("TOPPADDING",(0,0), (-1,-1), 5),
    ]))
    story += [sig_t, Spacer(1, 4*mm),
              para(footer_text, align="center", size=7, color="#888899")]

    doc.build(story)
    return buffer.getvalue()


def apply_pdf_password(pdf_bytes: bytes, password: str) -> bytes:
    """Password-protect PDF bytes using pypdf."""
    try:
        from pypdf import PdfReader, PdfWriter
    except ImportError:
        return pdf_bytes   # return unprotected if pypdf not installed

    reader = PdfReader(io.BytesIO(pdf_bytes))
    writer = PdfWriter()
    for page in reader.pages:
        writer.add_page(page)
    writer.encrypt(user_password=password, owner_password=None, use_128bit=True)
    out = io.BytesIO()
    writer.write(out)
    return out.getvalue()


def get_slip_password(slip_data: dict, password_type: str,
                      custom_password: Optional[str] = None) -> Optional[str]:
    """Derive PDF password: dob → DDMMYYYY, employee_id → code, custom → value."""
    if password_type == "dob":
        dob = slip_data.get("date_of_birth")
        if dob:
            return dob.strftime("%d%m%Y") if hasattr(dob, "strftime") else str(dob).replace("-", "")[6:] + str(dob).replace("-", "")[4:6] + str(dob).replace("-", "")[:4]
        return slip_data.get("employee_code", "password")
    elif password_type == "employee_id":
        return slip_data.get("employee_code", "password")
    elif password_type == "custom":
        return custom_password or "password"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# EMAIL DISPATCH  (merged from slip_email_service.py)
# ─────────────────────────────────────────────────────────────────────────────

def _build_email_body(slip: SalarySlip, template: str) -> str:
    month_label = f"{MONTH_NAMES[slip.slip_month]} {slip.slip_year}"
    return (template
            .replace("[Employee Name]", slip.employee_name)
            .replace("[Month Year]",    month_label)
            .replace("[Net Pay]",       f"₹{slip.net_pay:,.2f}"))


def _build_subject(slip: SalarySlip, template: str) -> str:
    month_label = f"{MONTH_NAMES[slip.slip_month]} {slip.slip_year}"
    return (template
            .replace("[Month Year]",    month_label)
            .replace("[Employee Name]", slip.employee_name))


def _slip_to_dict(slip: SalarySlip) -> dict:
    return dict(
        employee_id      = slip.employee_id,
        employee_code    = slip.employee_code,
        employee_name    = slip.employee_name,
        department       = slip.department,
        designation      = slip.designation,
        pan_number       = slip.pan_number,
        uan_number       = slip.uan_number,
        bank_account     = slip.bank_account,
        bank_name        = slip.bank_name,
        slip_month       = slip.slip_month,
        slip_year        = slip.slip_year,
        days_in_month    = slip.days_in_month,
        days_worked      = slip.days_worked,
        days_absent      = slip.days_absent,
        lop_days         = slip.lop_days,
        gross_salary     = slip.gross_salary,
        total_earnings   = slip.total_earnings,
        total_deductions = slip.total_deductions,
        net_pay          = slip.net_pay,
    )


async def send_slip_email(
    db: Session,
    slip_id: int,
    settings: SlipSettings,
    sent_by: Optional[str] = None,
    recipient_override: Optional[str] = None,
) -> SlipDistributionLog:
    """Generate PDF and email it to the employee. Logs every attempt."""
    from services.Payroll.slip_service import get_salary_slip, get_components, log_distribution

    slip       = get_salary_slip(db, slip_id)
    recipient  = recipient_override or slip.official_email
    if not recipient:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"No email address for {slip.employee_name}. Pass recipient_email in body.",
        )

    components = get_components(db, slip_id)
    slip_dict  = _slip_to_dict(slip)
    comp_list  = [dict(component_type=c.component_type, component_name=c.component_name,
                       component_code=c.component_code, amount=c.amount,
                       is_statutory=c.is_statutory) for c in components]

    pdf_bytes = generate_pdf_bytes(
        slip_data            = slip_dict,
        components           = comp_list,
        company_name         = settings.company_name or "Company",
        company_address      = settings.company_address or "",
        signatory_name       = settings.signatory_name or "HR Manager",
        footer_text          = settings.footer_text or "",
        confidentiality_note = settings.confidentiality_note or "",
    )

    password = None
    if settings.password_protect:
        password  = get_slip_password(slip_dict, settings.password_type or "dob",
                                      settings.custom_password)
        if password:
            pdf_bytes = apply_pdf_password(pdf_bytes, password)

    subject_tmpl = settings.email_subject_template or "Your Salary Slip for [Month Year]"
    body_tmpl    = settings.email_body_template or (
        "Dear [Employee Name],\n\nPlease find attached your salary slip for [Month Year].\n\n"
        "Net Pay: [Net Pay]\n\nRegards,\nHR Department"
    )
    subject = _build_subject(slip, subject_tmpl)
    body    = _build_email_body(slip, body_tmpl)
    if password:
        body += f"\n\nPDF Password: {password}"

    month_label = f"{MONTH_NAMES[slip.slip_month]}_{slip.slip_year}"
    filename    = f"SalarySlip_{slip.employee_code}_{month_label}.pdf"

    error_msg  = None
    log_status = "sent"
    try:
        message = MessageSchema(
            subject     = subject,
            recipients  = [recipient],
            body        = body,
            subtype     = MessageType.plain,
            attachments = [{"file": io.BytesIO(pdf_bytes),
                            "filename": filename,
                            "mime_type": "application/pdf"}],
        )
        await FastMail(mail_config).send_message(message)
        slip.is_emailed = True
        db.commit()
    except Exception as e:
        log_status = "failed"
        error_msg  = str(e)

    log = log_distribution(
        db, slip_id, slip.employee_id, "email",
        sent_by=sent_by, recipient_email=recipient,
        log_status=log_status, error_message=error_msg,
    )

    if log_status == "failed":
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Email send failed: {error_msg}",
        )
    return log


async def bulk_send_slip_emails(
    db: Session,
    slip_month: int,
    slip_year: int,
    settings: SlipSettings,
    sent_by: Optional[str] = None,
) -> dict:
    """Email all published slips for a period."""
    slips = db.execute(
        select(SalarySlip).where(
            SalarySlip.slip_month  == slip_month,
            SalarySlip.slip_year   == slip_year,
            SalarySlip.is_published == True,
            SalarySlip.is_deleted  == False,
        )
    ).scalars().all()

    if not slips:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No published slips for {MONTH_NAMES[slip_month]} {slip_year}. Publish slips first.",
        )

    success, failed = 0, []
    for slip in slips:
        try:
            await send_slip_email(db, slip.id, settings, sent_by=sent_by)
            success += 1
        except Exception as e:
            failed.append({"slip_id": slip.id, "employee": slip.employee_name, "error": str(e)})

    return {"total": len(slips), "success": success, "failed": len(failed), "errors": failed}


# ─────────────────────────────────────────────────────────────────────────────
# BULK ZIP  (merged from slip_zip_service.py)
# ─────────────────────────────────────────────────────────────────────────────

def generate_bulk_zip(
    db: Session,
    slip_month: int,
    slip_year: int,
    settings: SlipSettings,
    downloaded_by: Optional[str] = None,
) -> tuple:
    """
    Pack all salary slip PDFs for a period into a single ZIP.
    Returns (zip_bytes, zip_filename).
    """
    from services.Payroll.slip_service import get_components, log_distribution

    slips = db.execute(
        select(SalarySlip).where(
            SalarySlip.slip_month == slip_month,
            SalarySlip.slip_year  == slip_year,
            SalarySlip.is_deleted == False,
        )
    ).scalars().all()

    if not slips:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No slips found for {MONTH_NAMES[slip_month]} {slip_year}.",
        )

    zip_buf = io.BytesIO()
    with zipfile.ZipFile(zip_buf, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
        for slip in slips:
            components = get_components(db, slip.id)
            slip_dict  = _slip_to_dict(slip)
            comp_list  = [dict(component_type=c.component_type, component_name=c.component_name,
                               component_code=c.component_code, amount=c.amount,
                               is_statutory=c.is_statutory) for c in components]
            try:
                pdf = generate_pdf_bytes(
                    slip_data            = slip_dict,
                    components           = comp_list,
                    company_name         = settings.company_name or "Company",
                    company_address      = settings.company_address or "",
                    signatory_name       = settings.signatory_name or "HR Manager",
                    footer_text          = settings.footer_text or "",
                    confidentiality_note = settings.confidentiality_note or "",
                )
                if settings.password_protect:
                    pwd = get_slip_password(slip_dict, settings.password_type or "dob",
                                            settings.custom_password)
                    if pwd:
                        pdf = apply_pdf_password(pdf, pwd)

                fname = f"SalarySlip_{slip.employee_code}_{MONTH_NAMES[slip_month]}_{slip_year}.pdf"
                zf.writestr(fname, pdf)

                log_distribution(db, slip.id, slip.employee_id, "download",
                                 sent_by=downloaded_by, log_status="sent")
            except Exception as e:
                zf.writestr(f"ERROR_{slip.employee_code}.txt", f"Failed: {e}")

    db.commit()
    zip_buf.seek(0)
    return zip_buf.read(), f"SalarySlips_{MONTH_NAMES[slip_month]}_{slip_year}.zip"
