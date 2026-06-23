
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select, func
from calendar import month_name

from core.database import get_db
from model.Payroll.payroll_run import PayrollRun, PayrollRunDetail
from model.Payroll.salary_slip import SalarySlip

router = APIRouter(prefix="/payroll-reports", tags=["Payroll"])


@router.get("/summary")
def payroll_summary(
    year: int = Query(...),
    month: int = Query(..., ge=1, le=12),
    db: Session = Depends(get_db),
):
    run = db.execute(
        select(PayrollRun).where(
            PayrollRun.run_year == year,
            PayrollRun.run_month == month,
        )
    ).scalar_one_or_none()

    if not run:
        return {
            "year": year,
            "month": month,
            "month_name": month_name[month],
            "total_gross": 0,
            "total_deductions": 0,
            "total_net_pay": 0,
            "department_breakdown": [],
            "note": "No payroll run found for this period",
        }

    details = db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run.id)
    ).scalars().all()

    dept_map: dict = {}
    for d in details:
        dept = d.department or "Unknown"
        if dept not in dept_map:
            dept_map[dept] = {
                "department": dept,
                "employee_count": 0,
                "total_gross": 0.0,
                "total_deductions": 0.0,
                "total_net_pay": 0.0,
            }
        dept_map[dept]["employee_count"] += 1
        dept_map[dept]["total_gross"] += float(d.gross_salary or 0)
        dept_map[dept]["total_deductions"] += float(d.total_deductions or 0)
        dept_map[dept]["total_net_pay"] += float(d.net_pay or 0)

    # Round for clean output
    for v in dept_map.values():
        v["total_gross"] = round(v["total_gross"], 2)
        v["total_deductions"] = round(v["total_deductions"], 2)
        v["total_net_pay"] = round(v["total_net_pay"], 2)

    return {
        "year": year,
        "month": month,
        "month_name": month_name[month],
        "payroll_run_id": run.id,
        "status": run.status,
        "total_employees": run.total_employees,
        "total_gross": float(run.total_gross or 0),
        "total_deductions": float(run.total_deductions or 0),
        "total_net_pay": float(run.total_net_pay or 0),
        "department_breakdown": list(dept_map.values()),
    }


@router.get("/employee/{employee_id}")
def employee_payroll_history(employee_id: int, db: Session = Depends(get_db)):
    # Pull from salary slips for full history
    slips = db.execute(
        select(SalarySlip)
        .where(SalarySlip.employee_id == employee_id)
        .order_by(SalarySlip.slip_year.desc(), SalarySlip.slip_month.desc())
    ).scalars().all()

    # Also pull PayrollRunDetails to enrich with deduction breakdown
    run_details = db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.employee_id == employee_id)
    ).scalars().all()
    detail_index = {(d.payroll_run_id): d for d in run_details}

    history = []
    for s in slips:
        detail = detail_index.get(s.payroll_run_id)
        entry: dict = {
            "slip_id": s.id,
            "slip_month": s.slip_month,
            "month_name": month_name[s.slip_month],
            "slip_year": s.slip_year,
            "gross_salary": float(s.gross_salary or 0),
            "total_deductions": float(s.total_deductions or 0),
            "net_pay": float(s.net_pay or 0),
            "is_published": s.is_published,
        }
        if detail:
            entry["days_worked"] = detail.days_worked
            entry["days_absent"] = detail.days_absent
            entry["basic"] = float(detail.basic or 0)
            entry["hra"] = float(detail.hra or 0)
            entry["pf_employee"] = float(detail.pf_employee or 0)
            entry["tds"] = float(detail.tds or 0)
        history.append(entry)

    return {
        "employee_id": employee_id,
        "total_slips": len(history),
        "history": history,
    }


@router.get("/cost-breakdown/{run_id}")
def cost_breakdown(run_id: int, db: Session = Depends(get_db)):
    run = db.execute(select(PayrollRun).where(PayrollRun.id == run_id)).scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Payroll run not found")

    details = db.execute(
        select(PayrollRunDetail).where(PayrollRunDetail.payroll_run_id == run_id)
    ).scalars().all()

    total_basic = sum(float(d.basic or 0) for d in details)
    total_hra = sum(float(d.hra or 0) for d in details)
    total_special = sum(float(d.special_allowance or 0) for d in details)
    total_pf = sum(float(d.pf_employee or 0) for d in details)
    total_esi = sum(float(d.esi_employee or 0) for d in details)
    total_pt = sum(float(d.professional_tax or 0) for d in details)
    total_tds = sum(float(d.tds or 0) for d in details)

    return {
        "payroll_run_id": run_id,
        "run_month": run.run_month,
        "month_name": month_name[run.run_month],
        "run_year": run.run_year,
        "status": run.status,
        "total_employees": run.total_employees,
        "earnings_breakdown": {
            "total_basic": round(total_basic, 2),
            "total_hra": round(total_hra, 2),
            "total_special_allowance": round(total_special, 2),
            "total_gross": float(run.total_gross or 0),
        },
        "deductions_breakdown": {
            "total_pf_employee": round(total_pf, 2),
            "total_esi_employee": round(total_esi, 2),
            "total_professional_tax": round(total_pt, 2),
            "total_tds": round(total_tds, 2),
            "total_deductions": float(run.total_deductions or 0),
        },
        "total_net_pay": float(run.total_net_pay or 0),
        "employee_details": [
            {
                "employee_id": d.employee_id,
                "employee_code": d.employee_code,
                "employee_name": d.employee_name,
                "department": d.department,
                "days_worked": d.days_worked,
                "gross_salary": float(d.gross_salary or 0),
                "total_deductions": float(d.total_deductions or 0),
                "net_pay": float(d.net_pay or 0),
            }
            for d in details
        ],
    }
