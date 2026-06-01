from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from core.database import get_db

try:
    from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
except ImportError:
    PayrollRun = None
    PayrollRunDetail = None

try:
    from model.Payroll.salary_slip import SalarySlip
except ImportError:
    SalarySlip = None

router = APIRouter(prefix="/compliance", tags=["Reports"])


def _get_run_details_for_month(month: int, year: int, db: Session):
    """Helper: return PayrollRunDetail rows for a given month/year."""
    if PayrollRun is None or PayrollRunDetail is None:
        return []

    run = db.execute(
        select(PayrollRun).where(
            PayrollRun.run_month == month,
            PayrollRun.run_year == year,
        )
    ).scalars().first()

    if not run:
        return []

    try:
        details = db.execute(
            select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run.id)
        ).scalars().all()
        return details
    except Exception:
        # fallback if no FK relationship
        return db.execute(select(PayrollRunDetail)).scalars().all()


@router.get("/pf-report")
def pf_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    if PayrollRunDetail is None:
        return {
            "month": month,
            "year": year,
            "data": [],
            "message": "PayrollRunDetail model not available",
        }

    details = _get_run_details_for_month(month, year, db)

    data = []
    for d in details:
        pf_employee = getattr(d, "pf_employee", None)
        pf_employer = getattr(d, "pf_employer", None)
        data.append(
            {
                "employee_id": d.employee_id,
                "department": d.department,
                "gross_salary": float(d.gross_salary or 0),
                "pf_employee": float(pf_employee or 0),
                "pf_employer": float(pf_employer or 0),
                "total_pf": float((pf_employee or 0) + (pf_employer or 0)),
            }
        )

    return {
        "month": month,
        "year": year,
        "data": data,
        "total_pf": round(sum(r["total_pf"] for r in data), 2),
    }


@router.get("/esi-report")
def esi_report(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    if PayrollRunDetail is None:
        return {
            "month": month,
            "year": year,
            "data": [],
            "message": "PayrollRunDetail model not available",
        }

    details = _get_run_details_for_month(month, year, db)

    data = []
    for d in details:
        esi_employee = getattr(d, "esi_employee", None)
        esi_employer = getattr(d, "esi_employer", None)
        data.append(
            {
                "employee_id": d.employee_id,
                "department": d.department,
                "gross_salary": float(d.gross_salary or 0),
                "esi_employee": float(esi_employee or 0),
                "esi_employer": float(esi_employer or 0),
                "total_esi": float((esi_employee or 0) + (esi_employer or 0)),
            }
        )

    return {
        "month": month,
        "year": year,
        "data": data,
        "total_esi": round(sum(r["total_esi"] for r in data), 2),
    }


@router.get("/tds-report")
def tds_report(
    financial_year: str = Query(..., example="2024-25"),
    db: Session = Depends(get_db),
):
    if PayrollRunDetail is None:
        return {
            "financial_year": financial_year,
            "data": [],
            "message": "PayrollRunDetail model not available",
        }

    # Parse financial year e.g. "2024-25" -> months Apr 2024 - Mar 2025
    try:
        start_year = int(financial_year.split("-")[0])
        end_year = start_year + 1
    except (ValueError, IndexError):
        return {
            "financial_year": financial_year,
            "data": [],
            "message": "Invalid financial_year format. Use YYYY-YY e.g. 2024-25",
        }

    if PayrollRun is None:
        return {
            "financial_year": financial_year,
            "data": [],
            "message": "PayrollRun model not available",
        }

    # Apr-Dec of start_year + Jan-Mar of end_year
    runs = db.execute(
        select(PayrollRun).where(
            (
                (PayrollRun.run_year == start_year) & (PayrollRun.run_month >= 4)
            ) | (
                (PayrollRun.run_year == end_year) & (PayrollRun.run_month <= 3)
            )
        )
    ).scalars().all()

    run_ids = [r.id for r in runs]
    if not run_ids:
        return {"financial_year": financial_year, "data": [], "total_tds": 0}

    try:
        details = db.execute(
            select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id.in_(run_ids))
        ).scalars().all()
    except Exception:
        details = []

    # Aggregate TDS per employee
    emp_tds: dict = {}
    for d in details:
        emp_id = d.employee_id
        tds = float(getattr(d, "tds", None) or 0)
        if emp_id not in emp_tds:
            emp_tds[emp_id] = {
                "employee_id": emp_id,
                "department": d.department,
                "total_gross": 0.0,
                "total_tds": 0.0,
            }
        emp_tds[emp_id]["total_gross"] += float(d.gross_salary or 0)
        emp_tds[emp_id]["total_tds"] += tds

    data = list(emp_tds.values())
    return {
        "financial_year": financial_year,
        "data": data,
        "total_tds": round(sum(r["total_tds"] for r in data), 2),
    }
