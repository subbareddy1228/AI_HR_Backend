from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from core.database import get_db
from datetime import date

try:
    from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
except ImportError:
    PayrollRun = None
    PayrollRunDetail = None

try:
    from model.Payroll.salary_slip import SalarySlip
except ImportError:
    SalarySlip = None

router = APIRouter(prefix="/payroll", tags=["Reports"])


@router.get("/monthly-cost")
def monthly_cost(
    month: int = Query(..., ge=1, le=12),
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    if PayrollRun is None or PayrollRunDetail is None:
        return {
            "month": month,
            "year": year,
            "total_gross": 0,
            "total_net": 0,
            "total_deductions": 0,
            "by_department": [],
            "message": "PayrollRun model not available",
        }

    run = db.execute(
        select(PayrollRun).where(
            PayrollRun.run_month == month,
            PayrollRun.run_year == year,
        )
    ).scalars().first()

    if not run:
        return {
            "month": month,
            "year": year,
            "total_gross": 0,
            "total_net": 0,
            "total_deductions": 0,
            "by_department": [],
        }

    dept_rows = db.execute(
        select(
            PayrollRunDetail.department,
            func.sum(PayrollRunDetail.gross_salary).label("gross"),
            func.sum(PayrollRunDetail.net_pay).label("net"),
        )
        .where(PayrollRunDetail.payroll_run_id == run.id)
        .group_by(PayrollRunDetail.department)
    ).all() if hasattr(PayrollRunDetail, "payroll_run_id") else []

    # fallback: join via run id if available
    if not dept_rows:
        try:
            dept_rows = db.execute(
                select(
                    PayrollRunDetail.department,
                    func.sum(PayrollRunDetail.gross_salary).label("gross"),
                    func.sum(PayrollRunDetail.net_pay).label("net"),
                ).group_by(PayrollRunDetail.department)
            ).all()
        except Exception:
            dept_rows = []

    by_dept = [
        {
            "department": r.department or "Unknown",
            "gross": float(r.gross or 0),
            "net": float(r.net or 0),
            "deductions": float((r.gross or 0) - (r.net or 0)),
        }
        for r in dept_rows
    ]

    total_gross = float(run.total_gross or 0)
    total_net = float(run.total_net_pay or 0)

    return {
        "month": month,
        "year": year,
        "total_gross": total_gross,
        "total_net": total_net,
        "total_deductions": round(total_gross - total_net, 2),
        "by_department": by_dept,
    }


@router.get("/annual-summary")
def annual_summary(
    year: int = Query(...),
    db: Session = Depends(get_db),
):
    if PayrollRun is None:
        return {
            "year": year,
            "monthly_summary": [],
            "message": "PayrollRun model not available",
        }

    rows = db.execute(
        select(PayrollRun).where(PayrollRun.run_year == year).order_by(PayrollRun.run_month)
    ).scalars().all()

    monthly: dict = {m: {"gross": 0, "net": 0, "deductions": 0} for m in range(1, 13)}
    for run in rows:
        m = run.run_month
        gross = float(run.total_gross or 0)
        net = float(run.total_net_pay or 0)
        monthly[m] = {"gross": gross, "net": net, "deductions": round(gross - net, 2)}

    return {
        "year": year,
        "monthly_summary": [
            {"month": m, **vals} for m, vals in monthly.items()
        ],
    }


@router.get("/employee-history/{employee_id}")
def employee_salary_history(employee_id: int, db: Session = Depends(get_db)):
    if SalarySlip is None:
        return {
            "employee_id": employee_id,
            "data": [],
            "message": "SalarySlip model not available",
        }

    slips = db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id)
        .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    ).scalars().all()

    data = [
        {
            "slip_month": slip.slip_month,
            "slip_year": slip.slip_year,
            "gross_salary": float(slip.gross_salary or 0),
            "net_pay": float(slip.net_pay or 0),
        }
        for slip in slips
    ]
    return {"employee_id": employee_id, "data": data, "count": len(data)}
